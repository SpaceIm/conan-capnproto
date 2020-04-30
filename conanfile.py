import os

from conans import ConanFile, AutoToolsBuildEnvironment, CMake, tools
from conans.errors import ConanInvalidConfiguration

class CapnprotoConan(ConanFile):
    name = "capnproto"
    description = "Cap'n Proto serialization/RPC system."
    license = "MIT"
    topics = ("conan", "capnproto", "serialization", "rpc")
    homepage = "https://capnproto.org"
    url = "https://github.com/conan-io/conan-center-index"
    exports_sources = "CMakeLists.txt"
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "lite": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "lite": False
    }

    _autotools = None
    _cmake = None

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    @property
    def _minimum_compilers_version(self):
        return {
            "Visual Studio": "15",
            "gcc": "5",
            "clang": "5",
            "apple-clang": "4.3",
        }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.settings.compiler.cppstd:
            tools.check_min_cppstd(self, 14)
        mininum_compiler_version = self._minimum_compilers_version.get(str(self.settings.compiler))
        if mininum_compiler_version and tools.Version(self.settings.compiler.version) < mininum_compiler_version:
            raise ConanInvalidConfiguration("Cap'n Proto doesn't support {0} {1}".format(self.settings.compiler, self.settings.compiler.version))
        if self.settings.compiler == "Visual Studio" and self.options.shared:
            raise ConanInvalidConfiguration("Cap'n Proto doesn't support shared libraries for Visual Studio")

    def requirements(self):
        if not self.options.lite:
            self.requires("openssl/1.1.1g")
            self.requires("zlib/1.2.11")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename(self.name + "-" + self.version, self._source_subfolder)

    def build(self):
        if self.settings.os == "Windows":
            cmake = self._configure_cmake()
            cmake.build()
        else:
            autotools = self._configure_autotools()
            autotools.make()

    def _configure_cmake(self):
        if self._cmake:
            return self._cmake
        self._cmake = CMake(self)
        self._cmake.definitions["BUILD_TESTING"] = False
        self._cmake.definitions["EXTERNAL_CAPNP"] = False
        self._cmake.definitions["CAPNP_LITE"] = self.options.lite
        self._cmake.configure(build_folder=self._build_subfolder)
        return self._cmake

    def _configure_autotools(self):
        if self._autotools:
            return self._autotools
        conf_args = [
            "--{}-shared".format("enable" if self.options.shared else "disable"),
            "--{}-static".format("disable" if self.options.shared else "enable"),
            "--with-external-capnp=no",
            "--with-zlib={}".format("no" if self.options.lite else "yes"),
            "--with-openssl={}".format("no" if self.options.lite else "yes"),
            "--disable-reflection={}".format("yes" if self.options.lite else "no")
        ]
        self._autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
        self._autotools.configure(configure_dir=self._source_subfolder, args=conf_args)
        return self._autotools

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_subfolder)
        if self.settings.os == "Windows":
            cmake = self._configure_cmake()
            cmake.install()
        else:
            autotools = self._configure_autotools()
            autotools.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = self._get_ordered_libs()
        if self.options.lite:
            self.cpp_info.defines.append("CAPNP_LITE=1")
        if self.settings.os == "Linux":
            self.cpp_info.system_libs.append("pthread")
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs.append("ws2_32")
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))

    def _get_ordered_libs(self):
        libs = []
        if not self.options.lite:
            # kj-async is a dependency of capnp-rpc, capnp-json, kj-http, kj-gzip and kj-tls
            libs.extend(["capnp-rpc", "capnp-json", "kj-http", "kj-gzip", "kj-tls", "kj-async", "capnpc"])
        # - capnp is a dependency of capnp-rpc and capnp-json
        # - kj is a dependency of capnp-rpc, capnp-json, kj-http, kj-gzip, kj-tls, kj-async, capnpc and capnp
        libs.extend(["capnp", "kj"])
        return libs
