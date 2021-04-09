from librespot.proto.Keyexchange import *
import platform


class Version:
    version = "0.0.1-SNAPSHOT"

    @staticmethod
    def platform() -> Platform:
        if platform.system() == "Windows":
            return Platform.PLATFORM_WIN32_X86
        if platform.system() == "Darwin":
            return Platform.PLATFORM_OSX_X86
        return Platform.PLATFORM_LINUX_X86
        pass

    @staticmethod
    def version_string():
        return "librespot-python " + Version.version

    @staticmethod
    def system_info_string():
        return Version.version_string(
        ) + "; Python " + platform.python_version() + "; " + platform.system()

    @staticmethod
    def standard_build_info() -> BuildInfo:
        return BuildInfo(product=Product.PRODUCT_CLIENT,
                         product_flags=[ProductFlags.PRODUCT_FLAG_NONE],
                         platform=Version.platform(),
                         version=112800721)
