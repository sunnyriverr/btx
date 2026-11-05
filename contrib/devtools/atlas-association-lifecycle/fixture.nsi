Unicode true
RequestExecutionLevel user
SilentInstall silent
SilentUnInstall silent
Name "Disposable BTX association component"
OutFile "${OUTPUT}"
InstallDir "${DESTINATION}"
!include "FileAssociation.nsh"

Function .onInit
  SetShellVarContext current
  SetRegView 64
FunctionEnd

Function un.onInit
  SetShellVarContext current
  SetRegView 64
FunctionEnd

Section
  SetOutPath "$INSTDIR"
  !insertmacro APP_ASSOCIATE "${EXTENSION}" "${FILECLASS}" "Disposable association fixture" "$\"$INSTDIR\inert.exe$\",0" "Open with fixture" "$\"$INSTDIR\inert.exe$\" $\"%1$\""
  WriteUninstaller "$INSTDIR\uninstall.exe"
  IfErrors 0 +2
    Abort "Uninstaller creation failed"
SectionEnd

Section "Uninstall"
  !insertmacro APP_UNASSOCIATE "${EXTENSION}" "${FILECLASS}"
  Delete "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR"
  FileOpen $0 "${COMPLETION}" w
  FileWrite $0 "association-uninstall-finished"
  FileClose $0
SectionEnd
