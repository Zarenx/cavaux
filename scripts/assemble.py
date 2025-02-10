import os
import sys
import json
import argparse
import subprocess
import fileinput
import glob
import shutil

scriptPath    = os.path.realpath(__file__)
scriptRoot    = os.path.dirname(scriptPath)
PROJECTROOT   = os.path.dirname(os.path.dirname(scriptPath))

GIT           = os.path.join("git")
STEAMCMD      = os.path.join("steamcmd")
HEMTT         = os.path.join("hemtt")

KEYCREATE     = os.path.join("DSCreateKey")
KEYSIGN       = os.path.join("DSSignFile")
KEYCHECK      = os.path.join("DSCheckSignatures")

WORKDIR       = os.path.join(PROJECTROOT,".cavauxout")
WORKSHOPOUT   = os.path.join(WORKDIR,"steamapps","workshop","content","107410")
HEMTTRELEASE  = os.path.join(PROJECTROOT,".hemttout","release")
RELEASEFOLDER = os.path.join(PROJECTROOT,"releases")


def check_required_tools():
    toolsMissing = False
    print("Checking tools:")
    for tool in [GIT, STEAMCMD, HEMTT, KEYCREATE, KEYSIGN, KEYCHECK]:
        if shutil.which(tool):
            print(' > {}{}'.format(f"{tool}: ".ljust(12), shutil.which(tool)))
        else:
            print(' > {}Does not exist'.format(f"{tool}: ".ljust(12), shutil.which(tool)))
            toolsMissing = True
    if toolsMissing:
        print("\nError: Vital tools are missing\n       Make sure you have the required tools installed and is present in your PATH variable")
        sys.exit(1)
    print()


def get_and_set_version():
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        if result.returncode == 128:
            raise Exception("Warning: No git tags detected using 0.0.0 instead")
        tagVersion = result.stdout
        tagVersion = tagVersion.rstrip('\r\n')
    except Exception as e:
        tagVersion="0.0.0"

    tagVer = tagVersion.split('.')

    verMajor = tagVer[0]
    verMinor = tagVer[1]
    verPatch = tagVer[2]
    verBuild = 0

    hemttConf = os.path.join(PROJECTROOT,".hemtt","project.toml")
    modConf = os.path.join(PROJECTROOT,"mod.cpp")
    try: 
        def replaceAll(file,searchExp,replaceExp):
            for line in fileinput.input(file, inplace=1):
                if searchExp in line:
                    line = line.replace(searchExp,replaceExp)
                sys.stdout.write(line)
        replaceAll(hemttConf, "major = 0", f"major = {verMajor}")
        replaceAll(hemttConf, "minor = 0", f"minor = {verMinor}")
        replaceAll(hemttConf, "patch = 0", f"patch = {verPatch}")
        replaceAll(hemttConf, "build = 0", f"build = {verBuild}")

        replaceAll(modConf, "DevBuild", f"v{verMajor}.{verMinor}.{verPatch}.{verBuild}")
    except FileNotFoundError as e:
        print(e);sys.exit(1)

    return f"{verMajor}.{verMinor}.{verPatch}.{verBuild}"


def get_commit_id():
    result = subprocess.run(
        ['git','rev-parse','--short=8','HEAD'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    try:
        if result.returncode == 128:
            raise Exception("No git commitId detected using 'xxxxxxxx' instead")
        commitId = result.stdout
    except Exception as e:
        print(e)
        commitId="xxxxxxxx"

    commitId = commitId.replace('\n','')

    return commitId


def download_mod_files(complete_mod_list, STEAM_LOGIN, STEAM_PASS, verbose=False):
    # Check if password and username is set
    if STEAM_LOGIN == "" and STEAM_PASS == "":
        print("Warning: No steamcmd username and password provided skipping download")
        return
    elif STEAM_LOGIN == "":
        print("Warning: No steamcmd username provided skipping download")
        return
    elif STEAM_PASS == "":
        print("Warning: No steamcmd password provided skipping download")
        return

    login_cmd = [
        STEAMCMD,
        '+force_install_dir', WORKDIR,
        '+login', STEAM_LOGIN, STEAM_PASS,
    ]

    mods_cmd_parts = []
    for mod_id in complete_mod_list:
        mods_cmd_parts.extend(['+workshop_download_item', '107410', mod_id, 'validate'])

    full_cmd = login_cmd + mods_cmd_parts + ['+quit']

    if verbose:
        stdoutVar=None
    else:
        stdoutVar=subprocess.DEVNULL

    print(f"Downloading mods...")
    try:
        subprocess.run(full_cmd, shell=True, check=False, stdout=stdoutVar)
        print(f"Successfully downloaded mods")
    except subprocess.CalledProcessError as e:
        print(f"Failed to download mods: {e}")


def handle_hemtt_build(verbose=False):
    if verbose:
        stdoutVar=None
    else:
        stdoutVar=subprocess.DEVNULL
    subprocess.run(f"{HEMTT} release", shell=True, check=False, stdout=stdoutVar)



def main():
    parser = argparse.ArgumentParser(
        prog='assemble',
        description='This script will download mods from steam workshop, assemble them into a mod and create a release.')
    
    parser.add_argument('-u', '--username', type=str,
                        help='steam username (takes priority over the config file)')
    parser.add_argument('-p', '--password', type=str,
                        help='steam password (takes priority over the config file)')
    parser.add_argument('-C', '--config', type=str,
                        help='path to config file for username and password (Format: {"username": "","password": ""})')
    parser.add_argument('-t', '--tag', type=str,
                        help='(optional) this overwrites the version tag with the provided tag (Required format: 0.0.0.0)')
    parser.add_argument('-s', '--commit', type=str,
                        help='(optional) this defines the given current commit id')
    parser.add_argument('-d', '--data', type=str,
                        help='(optional) path to mod list json file (default: cavAuxModList.json)')
    parser.add_argument('--verbose', action='store_true',
                        help='(optional) show extended logging as well as allow you to use 2fa for steam login.')
    parser.add_argument('--dryrun', action='store_false',
                        help='(optional) allow you to skip the download process and use preexisting cache instead')

    args = parser.parse_args()
    
    # handle Config
    serverConfig = {
        "username": "",
        "password": ""
    }
    if args.config:
        try: 
            configFile = open(args.config)
        except FileNotFoundError as e:
            print(e);sys.exit(1)
        configFileDict = json.load(configFile)
        configFile.close()
        if "username" in configFileDict:
            serverConfig.update({"username": configFileDict["username"]})
        if "password" in configFileDict:
            serverConfig.update({"password": configFileDict["password"]})
    if args.username:
        serverConfig.update({"username": args.username})
    if args.password:
        serverConfig.update({"password": args.password})

    # Checking required tools
    check_required_tools()

    providerFile = args.data if args.data else "cavAuxModList.json"

    # Obtain list
    modListPath = os.path.join(PROJECTROOT, providerFile)
    try: 
        modListFile = open(modListPath)
    except FileNotFoundError:
        print(f"[ScriptError] {modListPath} does not exist in project root")
    modListDict = json.load(modListFile)
    modListFile.close()


    # Checking mod list
    print("Checking and verifying mod list...")
    for category in modListDict.keys():
        if "workshop" in category:
            print(f"Checking {category} mods...") if args.verbose else ""
            for id in modListDict[category]:
                print(f"> {modListDict[category][id]['name']} [{id}]") if args.verbose else ""
                license = modListDict[category][id]['License']
                if license != "License permits":
                    print(f"  Non standard license agreement: '{license}'") if args.verbose else ""
    print() if args.verbose else ""


    # Create download and project working folder
    if not os.path.exists(WORKDIR):
        os.makedirs(WORKDIR)
    
    
    # Downloading mods from workshop
    print("Downloading mods from workshop...")
    if args.dryrun:
        subprocess.run(f"{STEAMCMD} +quit", shell=True, check=False)
        download_mod_files(modListDict['workshop'].keys(), serverConfig['username'], serverConfig["password"], args.verbose)
    else:
        print("Warning: Running with dryrun parameter. Will use preexisting downloaded cache instead")
    print() if args.verbose else ""

    # Check if mod have been downloaded properly and contain correct data
    print("Checking downloads...")
    try:
        downloadedMods = len(os.listdir(WORKSHOPOUT))
    except FileNotFoundError:
        print(f"Failed to discover any mods in {WORKSHOPOUT}")
        sys.exit(1)
    expectedDownloadedMods = len(modListDict['workshop'].keys())
    if downloadedMods != expectedDownloadedMods:
        print(f"[Error] Downloaded mod mismatch got {downloadedMods} expected {expectedDownloadedMods}")
        sys.exit(1)

    allModsExist=True
    for expectedMod in modListDict['workshop'].keys():
        if not expectedMod in os.listdir(WORKSHOPOUT):
            print(f"[Error] {modListDict['workshop'][expectedMod]['name']} [{expectedMod}] does not exist or have not download properly")
            allModsExist=False
        else:
            print(f"Mod {modListDict['workshop'][expectedMod]['name']} [{expectedMod}] successfully downloaded...") if args.verbose else ""

    if allModsExist:
        print("All mods successfully downloaded")
        print() if args.verbose else ""
    else: 
        sys.exit(1)


    # Assemble and build mod
    if args.tag:
        commit = args.tag
    else:
        version = get_and_set_version()

    if args.commit:
        commit = args.commit
    else:
        commit = get_commit_id()
    print() if args.verbose else ""

    print("Building main addon")
    handle_hemtt_build(args.verbose)
    print() if args.verbose else ""

    releaseFolder = os.path.join(WORKDIR,'release')
    releaseAddonFolder = os.path.join(releaseFolder,"addons")
    releaseKeysFolder = os.path.join(releaseFolder,"keys")
    if not os.path.exists(releaseFolder):
        os.makedirs(releaseFolder)
    if not os.path.exists(releaseAddonFolder):
        os.makedirs(releaseAddonFolder)
    if not os.path.exists(releaseKeysFolder):
        os.makedirs(releaseKeysFolder)


    # Copying mods
    for id in os.listdir(WORKSHOPOUT):
        for pbo in glob.glob(os.path.join(WORKSHOPOUT,id,'addons','*.pbo'), recursive=True):
            print(f"Copying {os.path.basename(pbo)}") if args.verbose else ""
            shutil.copy2(os.path.join(pbo), releaseAddonFolder)


    # Copying over main mod
    shutil.copy2(os.path.join(HEMTTRELEASE,"mod.cpp"), releaseFolder)
    shutil.copy2(os.path.join(HEMTTRELEASE,"meta.cpp"), releaseFolder)
    shutil.copy2(os.path.join(HEMTTRELEASE,"logo_cavaux_ca.paa"), releaseFolder)
    for pbo in glob.glob(os.path.join(HEMTTRELEASE,'addons','*.pbo')):
        shutil.copy2(pbo, releaseAddonFolder)

    # Remove releases cause we make our own
    for hemttZip in glob.glob(os.path.join(RELEASEFOLDER,'*.zip')):
        os.remove(os.path.join(RELEASEFOLDER, hemttZip))


    # Create keys
    print("Creating keys and resigning addons...")
    os.chdir(releaseKeysFolder)
    privateKeyName     = f"cavaux_{version}-{commit}"
    privateKeyFullName = f"{privateKeyName}.biprivatekey"
    print(f"Making '{privateKeyName}'...") if args.verbose else ""
    
    subprocess.run(
        [KEYCREATE, privateKeyName],
        shell=True, check=False
    )

    keys = glob.glob(os.path.join(releaseKeysFolder,'*'))

    # Check if successful
    if len(keys) == 0:
        print("[Error] No keys have been created")
        sys.exit(1)
    for key in keys:
        print(f"Key '{os.path.basename(key)}' have been created...") if args.verbose else ""


    # Signing PBOs
    os.chdir(releaseAddonFolder)
    for pbo in glob.glob(os.path.join(releaseAddonFolder,'*.pbo')):
        print(f"Signing {pbo}") if args.verbose else ""
        subprocess.run(
            [KEYSIGN, os.path.join(releaseKeysFolder,privateKeyFullName), pbo],
            shell=True, check=False
        )

        createdKey = glob.glob(os.path.join(releaseKeysFolder,f'{pbo}*.bisign'))
        if not len(createdKey) == 1:
            print(f"[Error] failed to sign {pbo}")
            sys.exit(1)
        print(f"Signing completed {createdKey[0]}") if args.verbose else ""


    # Check signing
    print(f"Checking project signature...")
    proc = subprocess.run(
        [KEYCHECK, "-deep", releaseAddonFolder, releaseKeysFolder],
        shell=True, check=False, capture_output=True, text=True
    )
    print(proc.stdout, end="")
    if proc.returncode >= 1:
        print(f"[Error] failed to sign pbos")
        sys.exit(1)
    print(f"Signing successful") if args.verbose else ""
    
    os.remove(os.path.join(releaseKeysFolder,privateKeyFullName))
    os.chdir(PROJECTROOT)


    # Creating archive
    print("Creating archive...")
    shutil.copytree(os.path.join(WORKDIR,'release'), os.path.join(RELEASEFOLDER,'@cavaux'), dirs_exist_ok=True)

    os.chdir(RELEASEFOLDER)
    shutil.make_archive(
        os.path.join(RELEASEFOLDER, f"cavaux-{version}"),
        'zip',
        base_dir='@cavaux'
    )
    for releaseZip in glob.glob(os.path.join(RELEASEFOLDER,'*.zip')):
        print(f"Created release: {os.path.join(RELEASEFOLDER, releaseZip)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted")
        sys.exit(1)