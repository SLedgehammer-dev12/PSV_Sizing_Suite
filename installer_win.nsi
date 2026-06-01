; PSV Sizing Suite v2.2.0 — Windows Installer (NSIS)
; Sertifikasız build — Windows Defender uyarısı verebilir

!define PRODUCT_NAME "PSV Sizing Suite"
!define PRODUCT_VERSION "v2.2.0"
!define PRODUCT_PUBLISHER "PSV Engineering"
!define PRODUCT_WEB_SITE "https://github.com/SLedgehammer-dev12/PSV_Sizing_Suite"

!define SETUP_NAME "PSV_Sizing_Suite_Setup_${PRODUCT_VERSION}"
!define APP_DIRNAME "PSV_Sizing_Suite_${PRODUCT_VERSION}"
!define APP_EXE "${APP_DIRNAME}.exe"

SetCompressor /SOLID lzma
RequestExecutionLevel admin

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ---------- Interface Settings ----------
!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "assets\banner.bmp"
!define MUI_HEADERIMAGE

; ---------- Pages ----------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ---------- Languages ----------
!insertmacro MUI_LANGUAGE "Turkish"
!insertmacro MUI_LANGUAGE "English"

; ---------- Installer Info ----------
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "dist\${SETUP_NAME}.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
InstallDirRegKey HKLM "Software\${PRODUCT_NAME}" ""

Section "Install"
  SetOutPath "$INSTDIR"
  
  ; Ana uygulama dosyaları
  File /r "dist\${APP_DIRNAME}\*.*"
  
  ; Kısayollar
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" \
    "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Kaldır (Uninstall).lnk" \
    "$INSTDIR\Uninstall.exe"
  CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" \
    "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  ; Registry — programs list
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "DisplayName" "${PRODUCT_NAME} ${PRODUCT_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegDWord HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "NoModify" 1
  WriteRegDWord HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
    "NoRepair" 1
SectionEnd

Section "Uninstall"
  RMDir /r "$INSTDIR"
  RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
  
  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
  DeleteRegKey HKLM "Software\${PRODUCT_NAME}"
SectionEnd
