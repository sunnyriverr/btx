; Atlas overrides for the NSIS association helpers included by Tauri.
; Based on FileAssociation.nsh by Saivert, improved by Nikku.
; Keep the generated installer and its remaining lifecycle logic unchanged.
!include LogicLib.nsh

!ifmacrodef APP_ASSOCIATE
  !macroundef APP_ASSOCIATE
!endif
!macro APP_ASSOCIATE EXT FILECLASS DESCRIPTION ICON COMMANDTEXT COMMAND
  ReadRegStr $R0 SHELL_CONTEXT "Software\Classes\.${EXT}" ""
  ; A reinstall must not replace the original backup with our own class.
  ${If} $R0 != "${FILECLASS}"
    WriteRegStr SHELL_CONTEXT "Software\Classes\.${EXT}" "${FILECLASS}_backup" "$R0"
  ${EndIf}
  WriteRegStr SHELL_CONTEXT "Software\Classes\.${EXT}" "" "${FILECLASS}"
  WriteRegStr SHELL_CONTEXT "Software\Classes\${FILECLASS}" "" `${DESCRIPTION}`
  WriteRegStr SHELL_CONTEXT "Software\Classes\${FILECLASS}\DefaultIcon" "" `${ICON}`
  WriteRegStr SHELL_CONTEXT "Software\Classes\${FILECLASS}\shell" "" "open"
  WriteRegStr SHELL_CONTEXT "Software\Classes\${FILECLASS}\shell\open" "" `${COMMANDTEXT}`
  WriteRegStr SHELL_CONTEXT "Software\Classes\${FILECLASS}\shell\open\command" "" `${COMMAND}`
!macroend

!ifmacrodef APP_UNASSOCIATE
  !macroundef APP_UNASSOCIATE
!endif
!macro APP_UNASSOCIATE EXT FILECLASS
  ReadRegStr $R0 SHELL_CONTEXT "Software\Classes\.${EXT}" ""
  ; A later handler selection belongs to its new owner.
  ${If} $R0 == "${FILECLASS}"
    ReadRegStr $R0 SHELL_CONTEXT "Software\Classes\.${EXT}" "${FILECLASS}_backup"
    ${If} $R0 == ""
    ${OrIf} $R0 == "${FILECLASS}"
      ; Older installers may already have saved a self-reference. Do not
      ; restore a class that this uninstall is about to remove.
      DeleteRegValue SHELL_CONTEXT "Software\Classes\.${EXT}" ""
    ${Else}
      WriteRegStr SHELL_CONTEXT "Software\Classes\.${EXT}" "" "$R0"
    ${EndIf}
  ${EndIf}
  DeleteRegValue SHELL_CONTEXT "Software\Classes\.${EXT}" "${FILECLASS}_backup"
  DeleteRegKey SHELL_CONTEXT "Software\Classes\${FILECLASS}"
!macroend
