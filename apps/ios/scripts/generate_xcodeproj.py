"""Write a self-contained Xcode pbxproj + shared scheme for BankCore iOS."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWIFT = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "BankCore").rglob("*.swift"))
ASSETS = "BankCore/Assets.xcassets"
INFO = "BankCore/Info.plist"


def pid(*parts: str) -> str:
    return hashlib.sha1(("bankcore-ios:" + "/".join(parts)).encode()).hexdigest()[:24].upper()


PROJECT = pid("project")
TARGET = pid("target")
PRODUCT = pid("product")
MAIN_GROUP = pid("group", "main")
PRODUCTS_GROUP = pid("group", "products")
SOURCES_GROUP = pid("group", "sources")
SRC_PHASE = pid("phase", "sources")
RES_PHASE = pid("phase", "resources")
FW_PHASE = pid("phase", "frameworks")
PROJ_CFG = pid("cfglist", "project")
TGT_CFG = pid("cfglist", "target")
PROJ_DBG = pid("cfg", "project", "debug")
PROJ_REL = pid("cfg", "project", "release")
TGT_DBG = pid("cfg", "target", "debug")
TGT_REL = pid("cfg", "target", "release")
ASSETS_REF = pid("file", ASSETS)
ASSETS_BUILD = pid("build", ASSETS)
INFO_REF = pid("file", INFO)


def file_ref(rel: str) -> str:
    return pid("file", rel)


def build_file(rel: str) -> str:
    return pid("build", rel)


def group_id(*parts: str) -> str:
    return pid("group", *parts)


COMMON_PROJECT = """
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				CLANG_ENABLE_OBJC_WEAK = YES;
				CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING = YES;
				CLANG_WARN_BOOL_CONVERSION = YES;
				CLANG_WARN_COMMA = YES;
				CLANG_WARN_CONSTANT_CONVERSION = YES;
				CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS = YES;
				CLANG_WARN_DIRECT_OBJC_ISA_USAGE = YES_ERROR;
				CLANG_WARN_DOCUMENTATION_COMMENTS = YES;
				CLANG_WARN_EMPTY_BODY = YES;
				CLANG_WARN_ENUM_CONVERSION = YES;
				CLANG_WARN_INFINITE_RECURSION = YES;
				CLANG_WARN_INT_CONVERSION = YES;
				CLANG_WARN_NON_LITERAL_NULL_CONVERSION = YES;
				CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES;
				CLANG_WARN_OBJC_LITERAL_CONVERSION = YES;
				CLANG_WARN_OBJC_ROOT_CLASS = YES_ERROR;
				CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER = YES;
				CLANG_WARN_RANGE_LOOP_ANALYSIS = YES;
				CLANG_WARN_STRICT_PROTOTYPES = YES;
				CLANG_WARN_SUSPICIOUS_MOVE = YES;
				CLANG_WARN_UNGUARDED_AVAILABILITY = YES_AGGRESSIVE;
				CLANG_WARN_UNREACHABLE_CODE = YES;
				CLANG_WARN__DUPLICATE_METHOD_MATCH = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = dwarf;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_USER_SCRIPT_SANDBOXING = YES;
				GCC_C_LANGUAGE_STANDARD = gnu17;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_WARN_64_TO_32_BIT_CONVERSION = YES;
				GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;
				GCC_WARN_UNDECLARED_SELECTOR = YES;
				GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
				GCC_WARN_UNUSED_FUNCTION = YES;
				GCC_WARN_UNUSED_VARIABLE = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				LOCALIZATION_PREFERS_STRING_CATALOGS = YES;
				MTL_FAST_MATH = YES;
				SDKROOT = iphoneos;
				SWIFT_VERSION = 5.0;
""".rstrip("\n")


def pbx() -> str:
    lines: list[str] = []
    lines.append("// !$*UTF8*$!")
    lines.append("{")
    lines.append("\tarchiveVersion = 1;")
    lines.append("\tclasses = {")
    lines.append("\t};")
    lines.append("\tobjectVersion = 56;")
    lines.append("\tobjects = {")

    lines.append("\n/* Begin PBXBuildFile section */")
    for rel in SWIFT:
        lines.append(
            f"\t\t{build_file(rel)} /* {Path(rel).name} in Sources */ = "
            f"{{isa = PBXBuildFile; fileRef = {file_ref(rel)} /* {Path(rel).name} */; }};"
        )
    lines.append(
        f"\t\t{ASSETS_BUILD} /* Assets.xcassets in Resources */ = "
        f"{{isa = PBXBuildFile; fileRef = {ASSETS_REF} /* Assets.xcassets */; }};"
    )
    lines.append("/* End PBXBuildFile section */\n")

    lines.append("/* Begin PBXFileReference section */")
    lines.append(
        f"\t\t{PRODUCT} /* BankCore.app */ = {{isa = PBXFileReference; "
        f"explicitFileType = wrapper.application; includeInIndex = 0; "
        f"path = BankCore.app; sourceTree = BUILT_PRODUCTS_DIR; }};"
    )
    lines.append(
        f"\t\t{INFO_REF} /* Info.plist */ = {{isa = PBXFileReference; "
        f"lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = \"<group>\"; }};"
    )
    lines.append(
        f"\t\t{ASSETS_REF} /* Assets.xcassets */ = {{isa = PBXFileReference; "
        f"lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = \"<group>\"; }};"
    )
    for rel in SWIFT:
        name = Path(rel).name
        lines.append(
            f"\t\t{file_ref(rel)} /* {name} */ = {{isa = PBXFileReference; "
            f"lastKnownFileType = sourcecode.swift; path = {name}; sourceTree = \"<group>\"; }};"
        )
    lines.append("/* End PBXFileReference section */\n")

    lines.append("/* Begin PBXFrameworksBuildPhase section */")
    lines.append(f"\t\t{FW_PHASE} /* Frameworks */ = {{")
    lines.append("\t\t\tisa = PBXFrameworksBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXFrameworksBuildPhase section */\n")

    children_by_dir: dict[str, list[str]] = {}
    for rel in SWIFT:
        parent = str(Path(rel).parent).replace("\\", "/")
        children_by_dir.setdefault(parent, []).append(rel)
    children_by_dir.setdefault("BankCore", [])
    extra_dirs: set[str] = set()
    for d in list(children_by_dir):
        p = Path(d)
        while str(p) not in ("BankCore", ".", ""):
            extra_dirs.add(str(p).replace("\\", "/"))
            p = p.parent
    all_dirs = sorted(set(children_by_dir) | extra_dirs | {"BankCore"})

    def group_children(directory: str) -> list[str]:
        out: list[str] = []
        subs = [d for d in all_dirs if d != directory and Path(d).parent.as_posix() == directory]
        for sub in sorted(subs):
            out.append(f"\t\t\t\t{group_id(sub)} /* {Path(sub).name} */,")
        if directory == "BankCore":
            out.append(f"\t\t\t\t{ASSETS_REF} /* Assets.xcassets */,")
            out.append(f"\t\t\t\t{INFO_REF} /* Info.plist */,")
        for rel in sorted(children_by_dir.get(directory, [])):
            out.append(f"\t\t\t\t{file_ref(rel)} /* {Path(rel).name} */,")
        return out

    lines.append("/* Begin PBXGroup section */")
    lines.append(f"\t\t{MAIN_GROUP} = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    lines.append(f"\t\t\t\t{group_id('BankCore')} /* BankCore */,")
    lines.append(f"\t\t\t\t{PRODUCTS_GROUP} /* Products */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")
    lines.append(f"\t\t{PRODUCTS_GROUP} /* Products */ = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    lines.append(f"\t\t\t\t{PRODUCT} /* BankCore.app */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = Products;")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")
    for directory in all_dirs:
        name = Path(directory).name
        lines.append(f"\t\t{group_id(directory)} /* {name} */ = {{")
        lines.append("\t\t\tisa = PBXGroup;")
        lines.append("\t\t\tchildren = (")
        lines.extend(group_children(directory))
        lines.append("\t\t\t);")
        lines.append(f"\t\t\tpath = {name};")
        lines.append("\t\t\tsourceTree = \"<group>\";")
        lines.append("\t\t};")
    lines.append("/* End PBXGroup section */\n")

    lines.append("/* Begin PBXNativeTarget section */")
    lines.append(f"\t\t{TARGET} /* BankCore */ = {{")
    lines.append("\t\t\tisa = PBXNativeTarget;")
    lines.append(
        f"\t\t\tbuildConfigurationList = {TGT_CFG} /* Build configuration list for PBXNativeTarget \"BankCore\" */;"
    )
    lines.append("\t\t\tbuildPhases = (")
    lines.append(f"\t\t\t\t{SRC_PHASE} /* Sources */,")
    lines.append(f"\t\t\t\t{FW_PHASE} /* Frameworks */,")
    lines.append(f"\t\t\t\t{RES_PHASE} /* Resources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tbuildRules = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tdependencies = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = BankCore;")
    lines.append("\t\t\tproductName = BankCore;")
    lines.append(f"\t\t\tproductReference = {PRODUCT} /* BankCore.app */;")
    lines.append("\t\t\tproductType = \"com.apple.product-type.application\";")
    lines.append("\t\t};")
    lines.append("/* End PBXNativeTarget section */\n")

    lines.append("/* Begin PBXProject section */")
    lines.append(f"\t\t{PROJECT} /* Project object */ = {{")
    lines.append("\t\t\tisa = PBXProject;")
    lines.append("\t\t\tattributes = {")
    lines.append("\t\t\t\tBuildIndependentTargetsInParallel = 1;")
    lines.append("\t\t\t\tLastSwiftUpdateCheck = 1500;")
    lines.append("\t\t\t\tLastUpgradeCheck = 1500;")
    lines.append("\t\t\t\tTargetAttributes = {")
    lines.append(f"\t\t\t\t\t{TARGET} = {{")
    lines.append("\t\t\t\t\t\tCreatedOnToolsVersion = 15.0;")
    lines.append("\t\t\t\t\t};")
    lines.append("\t\t\t\t};")
    lines.append("\t\t\t};")
    lines.append(f"\t\t\tbuildConfigurationList = {PROJ_CFG} /* Build configuration list for PBXProject \"BankCore\" */;")
    lines.append("\t\t\tcompatibilityVersion = \"Xcode 14.0\";")
    lines.append("\t\t\tdevelopmentRegion = \"pt-BR\";")
    lines.append("\t\t\thasScannedForEncodings = 0;")
    lines.append("\t\t\tknownRegions = (")
    lines.append("\t\t\t\t\"pt-BR\",")
    lines.append("\t\t\t\ten,")
    lines.append("\t\t\t\tBase,")
    lines.append("\t\t\t);")
    lines.append(f"\t\t\tmainGroup = {MAIN_GROUP};")
    lines.append(f"\t\t\tproductRefGroup = {PRODUCTS_GROUP} /* Products */;")
    lines.append("\t\t\tprojectDirPath = \"\";")
    lines.append("\t\t\tprojectRoot = \"\";")
    lines.append("\t\t\ttargets = (")
    lines.append(f"\t\t\t\t{TARGET} /* BankCore */,")
    lines.append("\t\t\t);")
    lines.append("\t\t};")
    lines.append("/* End PBXProject section */\n")

    lines.append("/* Begin PBXResourcesBuildPhase section */")
    lines.append(f"\t\t{RES_PHASE} /* Resources */ = {{")
    lines.append("\t\t\tisa = PBXResourcesBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    lines.append(f"\t\t\t\t{ASSETS_BUILD} /* Assets.xcassets in Resources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXResourcesBuildPhase section */\n")

    lines.append("/* Begin PBXSourcesBuildPhase section */")
    lines.append(f"\t\t{SRC_PHASE} /* Sources */ = {{")
    lines.append("\t\t\tisa = PBXSourcesBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    for rel in SWIFT:
        lines.append(f"\t\t\t\t{build_file(rel)} /* {Path(rel).name} in Sources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXSourcesBuildPhase section */\n")

    def cfg_block(oid: str, name: str, extra: str) -> list[str]:
        return [
            f"\t\t{oid} /* {name} */ = {{",
            "\t\t\tisa = XCBuildConfiguration;",
            "\t\t\tbuildSettings = {",
            extra,
            "\t\t\t};",
            f"\t\t\tname = {name};",
            "\t\t};",
        ]

    debug_proj = COMMON_PROJECT + """
				ENABLE_TESTABILITY = YES;
				GCC_DYNAMIC_NO_PIC = NO;
				GCC_OPTIMIZATION_LEVEL = 0;
				GCC_PREPROCESSOR_DEFINITIONS = (
					"DEBUG=1",
					"$(inherited)",
				);
				MTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;
				ONLY_ACTIVE_ARCH = YES;
				SWIFT_ACTIVE_COMPILATION_CONDITIONS = "DEBUG $(inherited)";
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
"""
    release_proj = COMMON_PROJECT + """
				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
				ENABLE_NS_ASSERTIONS = NO;
				MTL_ENABLE_DEBUG_INFO = NO;
				SWIFT_COMPILATION_MODE = wholemodule;
				VALIDATE_PRODUCT = YES;
"""
    target_settings = """
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 11025;
				DEVELOPMENT_TEAM = "";
				ENABLE_PREVIEWS = YES;
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = BankCore/Info.plist;
				INFOPLIST_KEY_CFBundleDisplayName = BankCore;
				INFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.finance";
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.10.25;
				PRODUCT_BUNDLE_IDENTIFIER = br.vortex.bankcore;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = NO;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = 1;
"""

    lines.append("/* Begin XCBuildConfiguration section */")
    lines.extend(cfg_block(PROJ_DBG, "Debug", debug_proj))
    lines.extend(cfg_block(PROJ_REL, "Release", release_proj))
    lines.extend(cfg_block(TGT_DBG, "Debug", target_settings))
    lines.extend(cfg_block(TGT_REL, "Release", target_settings))
    lines.append("/* End XCBuildConfiguration section */\n")

    def cfg_list(oid: str, title: str, dbg: str, rel: str) -> list[str]:
        return [
            f"\t\t{oid} /* {title} */ = {{",
            "\t\t\tisa = XCConfigurationList;",
            "\t\t\tbuildConfigurations = (",
            f"\t\t\t\t{dbg} /* Debug */,",
            f"\t\t\t\t{rel} /* Release */,",
            "\t\t\t);",
            "\t\t\tdefaultConfigurationIsVisible = 0;",
            "\t\t\tdefaultConfigurationName = Release;",
            "\t\t};",
        ]

    lines.append("/* Begin XCConfigurationList section */")
    lines.extend(cfg_list(PROJ_CFG, 'Build configuration list for PBXProject "BankCore"', PROJ_DBG, PROJ_REL))
    lines.extend(cfg_list(TGT_CFG, 'Build configuration list for PBXNativeTarget "BankCore"', TGT_DBG, TGT_REL))
    lines.append("/* End XCConfigurationList section */")

    lines.append("\t};")
    lines.append(f"\trootObject = {PROJECT} /* Project object */;")
    lines.append("}")
    return "\n".join(lines) + "\n"


def scheme() -> str:
    ref = f"""               BuildableIdentifier = "primary"
               BlueprintIdentifier = "{TARGET}"
               BuildableName = "BankCore.app"
               BlueprintName = "BankCore"
               ReferencedContainer = "container:BankCore.xcodeproj">"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1500"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            <BuildableReference
{ref}
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES"
      shouldAutocreateTestPlan = "YES">
   </TestAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
{ref}
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
{ref}
         </BuildableReference>
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
"""


def main() -> None:
    if not SWIFT:
        raise SystemExit("no Swift files found")
    proj_dir = ROOT / "BankCore.xcodeproj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "project.pbxproj").write_text(pbx(), encoding="utf-8")
    workspace = proj_dir / "project.xcworkspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "contents.xcworkspacedata").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<Workspace
   version = "1.0">
   <FileRef
      location = "self:">
   </FileRef>
</Workspace>
""",
        encoding="utf-8",
    )
    scheme_dir = proj_dir / "xcshareddata" / "xcschemes"
    scheme_dir.mkdir(parents=True, exist_ok=True)
    (scheme_dir / "BankCore.xcscheme").write_text(scheme(), encoding="utf-8")
    print(f"wrote project with {len(SWIFT)} Swift files")
    for rel in SWIFT:
        print(" ", rel)


if __name__ == "__main__":
    main()
