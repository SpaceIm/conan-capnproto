from conans import ConanFile, CMake, tools, AutoToolsBuildEnvironment
from conans.errors import ConanInvalidConfiguration
import glob
import os


class CapnprotoConan(ConanFile):
    name = "capnproto"
    description = "Cap'n Proto serialization/RPC system."
    license = "MIT"
    topics = ("conan", "capnproto", "serialization", "rpc")
    homepage = "https://capnproto.org"
    url = "https://github.com/conan-io/conan-center-index"
    exports_sources = ("CMakeLists.txt", "patches/*")
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openssl": [True, False],
        "with_zlib": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openssl": True,
        "with_zlib": True
    }

    _cmake = None
    _autotools = None

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
            del self.options.openssl

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        if self.settings.compiler.cppstd:
            tools.check_min_cppstd(self, 14)
        mininum_compiler_version = self._minimum_compilers_version.get(str(self.settings.compiler))
        if mininum_compiler_version and tools.Version(self.settings.compiler.version) < mininum_compiler_version:
            raise ConanInvalidConfiguration("Cap'n Proto doesn't support {0} {1}".format(self.settings.compiler, self.settings.compiler.version))
        if self.settings.compiler == "Visual Studio" and self.options.shared:
            raise ConanInvalidConfiguration("Cap'n Proto doesn't support shared libraries for Visual Studio")

    def requirements(self):
        if self.options.get_safe("with_openssl"):
            self.requires("openssl/1.1.1h")
        if self.options.with_zlib:
            self.requires("zlib/1.2.11")

    def build_requirements(self):
        if self.settings.os != "Windows":
            self.build_requires("autoconf/2.69")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        os.rename(self.name + "-" + self.version, self._source_subfolder)

    def _configure_cmake(self):
        if self._cmake:
            return self._cmake
        self._cmake = CMake(self)
        self._cmake.definitions["BUILD_TESTING"] = False
        self._cmake.definitions["EXTERNAL_CAPNP"] = False
        self._cmake.definitions["CAPNP_LITE"] = False
        self._cmake.configure(build_folder=self._build_subfolder)
        return self._cmake

    def _configure_autotools(self):
        if self._autotools:
            return self._autotools
        args = []
        if self.options.shared:
            args.extend(["--disable-static", "--enable-shared"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        args.append("--with-openssl" if self.options.with_openssl else "--without-openssl")
        args.append("--with-zlib" if self.options.with_zlib else "--without-zlib")
        args.append("--enable-reflection")
        self._autotools = AutoToolsBuildEnvironment(self)
        self._autotools.configure(args=args, configure_dir=os.path.join(self._source_subfolder, "c++"))
        return self._autotools

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        if self.settings.os == "Windows":
            cmake = self._configure_cmake()
            cmake.build()
        else:
            with tools.chdir(os.path.join(self._source_subfolder, "c++")):
                self.run("{} --install --verbose -Wall".format(tools.get_env("AUTORECONF")))
            autotools = self._configure_autotools()
            autotools.make()

    @property
    def _cmake_folder(self):
        return os.path.join("lib", "cmake", "CapnProto")

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_subfolder)
        if self.settings.os == "Windows":
            cmake = self._configure_cmake()
            cmake.install()
        else:
            autotools = self._configure_autotools()
            autotools.install()
            for la_file in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
                os.remove(la_file)
        for cmake_file in glob.glob(os.path.join(self.package_folder, self._cmake_folder, "*")):
            if os.path.basename(cmake_file) not in ["CapnProtoMacros.cmake", "CapnProtoTargets.cmake"]:
                os.remove(cmake_file)
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.names["cmake_find_package"] = "CapnProto"
        self.cpp_info.names["cmake_find_package_multi"] = "CapnProto"
        # capnp
        self.cpp_info.components["capnp"].names["cmake_find_package"] = "capnp"
        self.cpp_info.components["capnp"].names["cmake_find_package_multi"] = "capnp"
        self.cpp_info.components["capnp"].names["pkg_config"] = "capnp"
        self.cpp_info.components["capnp"].libs = ["capnp"]
        self.cpp_info.components["capnp"].requires = ["kj"]
        # capnp-json
        self.cpp_info.components["capnp-json"].names["cmake_find_package"] = "capnp-json"
        self.cpp_info.components["capnp-json"].names["cmake_find_package_multi"] = "capnp-json"
        self.cpp_info.components["capnp-json"].names["pkg_config"] = "capnp-json"
        self.cpp_info.components["capnp-json"].libs = ["capnp-json"]
        self.cpp_info.components["capnp-json"].requires = ["capnp", "kj"]
        # capnp-rpc
        self.cpp_info.components["capnp-rpc"].names["cmake_find_package"] = "capnp-rpc"
        self.cpp_info.components["capnp-rpc"].names["cmake_find_package_multi"] = "capnp-rpc"
        self.cpp_info.components["capnp-rpc"].names["pkg_config"] = "capnp-rpc"
        self.cpp_info.components["capnp-rpc"].libs = ["capnp-rpc"]
        self.cpp_info.components["capnp-rpc"].requires = ["capnp", "kj", "kj-async"]
        # kj
        self.cpp_info.components["kj"].names["cmake_find_package"] = "kj"
        self.cpp_info.components["kj"].names["cmake_find_package_multi"] = "kj"
        self.cpp_info.components["kj"].names["pkg_config"] = "kj"
        self.cpp_info.components["kj"].libs = ["kj"]
        if self.settings.os == "Linux":
            self.cpp_info.components["kj"].system_libs = ["pthread"]
        self.cpp_info.components["kj"].builddirs = self._cmake_folder
        self.cpp_info.components["kj"].build_modules = [os.path.join(self._cmake_folder, "CapnProtoMacros.cmake"),
                                                        os.path.join(self._cmake_folder, "CapnProtoTargets.cmake")]
        # kj-async
        self.cpp_info.components["kj-async"].names["cmake_find_package"] = "kj-async"
        self.cpp_info.components["kj-async"].names["cmake_find_package_multi"] = "kj-async"
        self.cpp_info.components["kj-async"].names["pkg_config"] = "kj-async"
        self.cpp_info.components["kj-async"].libs = ["kj-async"]
        if self.settings.os == "Linux":
            self.cpp_info.components["kj-async"].system_libs = ["pthread"]
        elif self.settings.os == "Windows":
            self.cpp_info.components["kj-async"].system_libs = ["ws2_32"]
        self.cpp_info.components["kj-async"].requires = ["kj"]
        # kj-http
        self.cpp_info.components["kj-http"].names["cmake_find_package"] = "kj-http"
        self.cpp_info.components["kj-http"].names["cmake_find_package_multi"] = "kj-http"
        self.cpp_info.components["kj-http"].names["pkg_config"] = "kj-http"
        self.cpp_info.components["kj-http"].libs = ["kj-http"]
        self.cpp_info.components["kj-http"].requires = ["kj", "kj-async"]
        # kj-gzip
        if self.options.with_zlib:
            self.cpp_info.components["kj-gzip"].names["cmake_find_package"] = "kj-gzip"
            self.cpp_info.components["kj-gzip"].names["cmake_find_package_multi"] = "kj-gzip"
            self.cpp_info.components["kj-gzip"].names["pkg_config"] = "kj-gzip"
            self.cpp_info.components["kj-gzip"].libs = ["kj-gzip"]
            self.cpp_info.components["kj-gzip"].requires = ["kj", "kj-async", "zlib::zlib"]
        # kj-tls
        if self.options.get_safe("with_openssl"):
            self.cpp_info.components["kj-tls"].names["cmake_find_package"] = "kj-tls"
            self.cpp_info.components["kj-tls"].names["cmake_find_package_multi"] = "kj-tls"
            self.cpp_info.components["kj-tls"].names["pkg_config"] = "kj-tls"
            self.cpp_info.components["kj-tls"].libs = ["kj-tls"]
            self.cpp_info.components["kj-tls"].requires = ["kj", "kj-async", "openssl::openssl"]

        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH env var with: {}".format(bin_path))
        self.env_info.PATH.append(bin_path)
