from conans import ConanFile, CMake, tools
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "cmake"

    def build(self):
        with tools.run_environment(self):
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not tools.cross_building(self.settings):
            bin_path = os.path.join("bin", "addressbook")
            self.run("{} write".format(bin_path), run_environment=True)
