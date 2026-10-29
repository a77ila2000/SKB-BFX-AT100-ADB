# 설치용 배포 이미지: 다운로드부터 첫 부팅까지

## 배포본의 범위

[Releases의 bfx12.1-vanilla-20261029-r1](https://github.com/a77ila2000/SKB-BFX-AT100-ADB/releases/tag/bfx12.1-vanilla-20261029-r1)에서 `bfx-at100-android12.1-vanilla-r1.zip`을 받습니다. 이는 **Android 9의 BFX-AT100에 적용하는 Android 12.1/API 32 vanilla system과 vbmeta**입니다. 제조사 업데이트 메뉴에 업로드하는 OTA ZIP이 아닙니다. 먼저 PC에서 압축을 풀어 사용합니다.

**r1은 실험 배포본(prerelease)**입니다. 기존 개인화 이미지에서는 USB 없는 완전 전원 부팅과 실제 TV의 PCM 소리를 확인했습니다. 이번에 키·시리얼을 제거하고 ADB 인증을 강화해 다시 만든 배포 이미지 자체는 오프라인 검증을 통과했으며, 기기에 다시 기록한 부팅 시험은 하지 않았습니다. 이 차이를 알고 사용해야 합니다.

런처, 별도 TV 설정 APK, Google 앱, 게임, 사용자 데이터는 추가하지 않았습니다. 따라서 작성자의 TBLZ 홈/TV 설정 화면과 처음 화면이 같지는 않습니다. 기본은 PHH vanilla UI이며, 전체 Android TV 인증 펌웨어가 아닙니다. 보안 패치는 **2022-07-05**입니다.

## 무엇을 제거·변경했나

- 사용 중인 기기 덤프를 복제하지 않고 해시가 고정된 깨끗한 PHH v416 원본에서 다시 구성했습니다.
- 작성자의 기기 시리얼, CID, MAC, 네트워크 주소와 ADB 키를 넣지 않았습니다. userdata·Wi-Fi 설정·계정·페어링 파일도 배포하지 않습니다.
- 오디오 수정의 개인 시리얼 조건을 제거했습니다. 대신 `ro.product.vendor.model=BFX-AT100`과 정확한 원본/수정 라이브러리 SHA-256이 일치할 때만 적용합니다.
- 원본 GSI의 `ro.adb.secure=0`을 **1**로 바꿨습니다. 기본 이미지에는 미리 승인된 PC가 없으며, TCP ADB 자동 시작 파일도 없습니다.
- 물리 UART 셸은 남겨 초기 설정·복구에 사용합니다. PHH 개발용 su도 기반 이미지에 포함됩니다. 정식 잠금 제품의 보안 수준을 제공하는 ROM은 아닙니다.

## 1. 적용 조건 확인

다음 조건이 모두 맞아야 합니다.

| 항목 | 대상 |
|---|---|
| 모델 | BFX-AT100 |
| 출발 펌웨어 | Android 9/API 28, `PI.15.520.8-20200731` 계열 중 아래 검증을 통과한 원본 |
| 파티션 | `super`가 없는 기존 정적 구조 |
| system | `0x5c800000` = 1,551,892,480바이트 |
| vbmeta | `0x200000` = 2,097,152바이트 |
| 원본 vbmeta 앞 4KiB SHA-256 | `8645abe07d046688991ddd4d2bbcba81a444e444eb83884b264fb4aff707b91d` |
| UART | 115200, 8N1, 흐름 제어 없음, 실제 U-Boot 프롬프트 접근 |
| RAM | 관측 보드는 3GiB. 예제의 RAM 범위가 사용 가능하고 부트로더와 겹치지 않아야 함 |

이미 SKB Android 12의 `super` 구조인 기기에는 이 절차를 적용하지 않습니다. 모델 이름이 같아도 vbmeta·원본 파티션 검증이 실패하면 중단합니다. AVB 비활성화나 다른 사람의 vendor·DTB 교체로 검증을 억지로 통과시키지 않습니다.

UART는 기판 TX↔변환기 RX, 기판 RX↔변환기 TX, GND↔GND입니다. VCC는 연결하지 않습니다. 실제 신호 전압과 변환기 호환성을 확인하고, 처음에는 RX만 수신합니다. [UART 소스](../src/serial-terminal.ps1)는 기본 RX이며 F2로 TX를 켜고 F10으로 닫습니다.

## 2. 자기 기기의 원본 백업 확보

쓰기 전에 전체 eMMC user area 및 boot0/boot1을 보관하고, PC에서 재읽기 해시를 확인합니다. 관측 기기의 user area는 7,818,182,656바이트, boot0/boot1은 각각 4MiB였습니다. RPMB는 이 백업에 포함되지 않습니다. 내부 Android 파일시스템이 마운트된 상태에서 만든 전체 덤프를 정지된 복구 백업과 같다고 보지 않습니다.

이 프로젝트에서는 구형 32비트 BusyBox `dd`의 큰 seek가 4GiB에서 반복되는 것을 발견했습니다. [read-range64.c](../src/read-range64.c)의 64비트 `pread` 방식과 순차 전체 해시로 검증했습니다. 백업 방법·기기 복구 경로를 확보하지 못한 경우 이미지 쓰기를 시작하지 않습니다.

검증에는 자신의 원본에서 얻은 아래 파일이 필요합니다. 작성자의 원본 덤프는 공개하지 않습니다.

```text
original-partitions/
  vbmeta.img
  boot.img
  recovery.img
  vendor.img
  product.img
  dtbo.img
  dtb.img
```

`system.img`, `env`, `misc` 등 원래 상태도 별도로 보관합니다. 전체 복구에는 userdata 등 다른 영역까지 필요할 수 있습니다. **다른 사용자의 env/misc/전체 덤프를 자신의 기기에 쓰지 않습니다.**

## 3. 다운로드 무결성 및 원본 호환성 검사

릴리스의 `SHA256SUMS-release.txt`는 ZIP 등 다운로드 파일의 해시입니다. ZIP 안의 `SHA256SUMS.txt`는 압축 해제된 두 이미지의 해시입니다. 먼저 다운로드한 ZIP 해시를 비교한 뒤 압축을 풉니다.

Windows:

```powershell
Get-FileHash .\bfx-at100-android12.1-vanilla-r1.zip -Algorithm SHA256
Expand-Archive .\bfx-at100-android12.1-vanilla-r1.zip .\bfx12-r1
Get-FileHash .\bfx12-r1\system.img, .\bfx12-r1\vbmeta.img -Algorithm SHA256
```

Linux/WSL에서는 저장소 소스와 [고정된 AOSP avbtool](https://android.googlesource.com/platform/external/avb/+/refs/tags/android-12.0.0_r34/avbtool.py)을 준비하고 실행합니다. tools 폴더의 avbtool.py는 해당 파일의 base64 TEXT 응답을 디코딩한 원본이어야 합니다.

```sh
sha256sum -c SHA256SUMS.txt
python3 /path/to/repository/src/check_release.py \
  /path/to/bfx12-r1 /path/to/original-partitions \
  --avbtool /path/to/tools/avbtool.py
```

`check_release.py`는 두 이미지의 크기·SHA-256·CRC32, 원본 vbmeta, 유지할 6개 원본 파티션의 AVB descriptor까지 검증합니다. 기기에 접속하거나 쓰지 않습니다. **마지막 PASS와 avbtool 성공을 모두 확인한 다음에만 진행합니다.**

## 4. USB와 U-Boot 준비

FAT32 USB에 아래 파일을 복사합니다. 이 예제의 파일은 각각 4GiB 미만입니다.

```text
USB 루트/
  aml_autoscript       ← ZIP의 uart-console/aml_autoscript를 복사
  bfx12/
    system.img
    vbmeta.img
```

`aml_autoscript`는 자동 설치기가 아닙니다. RAM의 부팅 변수만 바꾸어 U-Boot에서 수동 작업을 할 수 있게 합니다. `saveenv`나 flash 쓰기는 포함하지 않습니다. 원본은 [uboot-console.cmd](../src/uboot-console.cmd), 컨테이너 생성기는 [make_usb_script.py](../src/make_usb_script.py)입니다.

관측 기기에서는 USB 복구 경로가 이 파일을 읽었습니다. 보드 SW401의 용도를 모든 기기에 일반화하지 않습니다. UART에서 `BFX_UART_CONSOLE_READY`와 실제 프롬프트가 보이지 않으면 아직 쓰기 단계가 아닙니다. 단순 USB 삽입만으로 모든 기기에서 이 경로에 들어간다고 보장하지 않습니다.

U-Boot에서 먼저 `help store`, `help fatload`, `help crc32`, `mmcinfo`를 확인합니다. 이 문서가 사용하는 `store write 이름 RAM주소 오프셋 바이트수` 문법이 일치해야 합니다. 예제 RAM은 `0x20000000`부터 `0x7c800000` 직전까지이며, 관측 보드의 부트로더 재배치 주소는 그보다 위였습니다. 자신의 보드 메모리 지도가 다르면 주소를 복사하지 않습니다.

## 5. system을 RAM에 읽고 검증한 뒤 기록

**실제 U-Boot 프롬프트에서 한 단계씩 실행합니다.** `mmc dev 1`은 관측 기기의 내부 eMMC 번호입니다. 자기 기기의 mmcinfo로 내부 eMMC임을 확인한 뒤 사용합니다.

```text
mmc dev 1
mmcinfo
usb start
fatload usb 0 0x20000000 bfx12/system.img
printenv filesize
crc32 0x20000000 0x5c800000
```

`filesize=5c800000`, CRC32 **`a84257de`**가 나와야 합니다. 먼저 PC에서 SHA-256을 검증해야 하며 CRC32는 USB→RAM 전송 확인용입니다. 일치하지 않으면 기록하지 않습니다.

일치한 경우:

```text
store write system 0x20000000 0 0x5c800000
store read system 0x20000000 0 0x5c800000
crc32 0x20000000 0x5c800000
```

재읽기 CRC32도 **`a84257de`**여야 합니다. 기록 명령의 반환 상태와 읽기 오류 여부를 함께 확인합니다.

## 6. vbmeta도 같은 방식으로 기록

```text
fatload usb 0 0x20000000 bfx12/vbmeta.img
printenv filesize
crc32 0x20000000 0x200000
```

`filesize=200000`, CRC32 **`3e798e22`**를 확인한 경우에만:

```text
store write vbmeta 0x20000000 0 0x200000
store read vbmeta 0x20000000 0 0x200000
crc32 0x20000000 0x200000
```

재읽기 CRC32는 **`3e798e22`**여야 합니다. system과 vbmeta는 한 쌍입니다. 이전 system과 새 vbmeta 또는 반대 조합으로 부팅하지 않습니다. bootloader/vendor/DTB/super를 이 절차에서 쓰지 않습니다.

두 검증이 끝나면 RAM 변수 상태를 확인한 뒤 `run storeboot`로 정상 boot 파티션 부팅을 시도합니다. 이 시점의 성공만으로 USB 없는 전원 부팅까지 확인된 것은 아닙니다.

## 7. 첫 화면과 기존 Android 9 데이터 조정

이 ZIP은 userdata를 초기화하거나 작성자의 앱·설정을 복제하지 않습니다. 기존 Android 9 데이터가 남아 있다면 충돌이 발생할 수 있습니다. 첫 화면이 검을 때 무작정 다시 flash하지 말고 UART와 `logcat -b crash`에서 원인을 확인합니다.

이 프로젝트에서 확인한 Keyguard 충돌에 한해서 UART의 Android 셸에서:

```sh
su 0 pm disable-user --user 0 com.android.systemui/com.android.systemui.keyguard.KeyguardService
su 0 setprop ctl.restart zygote
```

구성요소 상태는 userdata에 저장되므로, 완전 초기화한 다른 기기에는 이 조정이 아직 적용돼 있지 않습니다. 원복은 같은 구성요소에 `pm enable --user 0`을 사용합니다. 기존 Google/B tv 앱의 시스템 권한 충돌이 보이면 [호환성 기록](compatibility.md)의 해당 증상과 연결해 사용자 단위 비활성화합니다. 패키지를 추측해 시스템 파일을 삭제하지 않습니다.

DHCP를 사용합니다. 이 구성에서 고정 IP gateway 레코드를 저장했다가 EthernetService 부팅 반복이 발생한 이력이 있습니다. 같은 stack이 있을 경우 자신의 `/data/misc/ethernet/ipconfig.txt`를 백업한 뒤 이름을 바꾸어 DHCP로 복구합니다.

기본 설정은 일반 vanilla Android입니다. 별도 TV 런처·TV 설정 APK는 이 배포본의 설치 완료 조건이나 동봉 파일이 아닙니다. 필요하면 별도로 준비합니다.

## 8. 자기 PC의 ADB 연결

원래 SKB 펌웨어의 `000923` 메뉴 PIN은 이 GSI의 ADB 비밀번호가 아닙니다. 배포본은 **`ro.adb.secure=1`**, 사전 승인 키 없음, TCP 자동 시작 없음입니다.

화면이 보이고 인증 창을 조작할 수 있을 때 개발자 옵션에서 디버깅을 켜거나, UART에서 필요한 시간 동안 TCP 연결을 시작할 수 있습니다.

```sh
su 0 settings put global adb_enabled 1
su 0 setprop service.adb.tcp.port 5555
su 0 setprop ctl.restart adbd
```

PC에서는 자기 기기의 DHCP 주소로 `adb connect STB_IP:5555`를 실행하고 TV의 RSA 승인 창을 확인합니다. `unauthorized`이면 승인 전이며 연결 완료가 아닙니다. 인증 창이 나오지 않으면 인증을 끄지 말고 아래 자체 빌드 방법으로 자기 공개키를 포함하거나 UART 진단을 계속합니다. 작업 후 `service.adb.tcp.port=-1` 및 adbd 재시작으로 TCP 리스닝을 끕니다.

화면 승인 없이 자기 PC를 미리 등록해야 할 경우 [빌드 안내](source-and-privacy.md)대로 **자신의 공개키 `adbkey.pub`만** `ADB_PUBLIC_KEY`로 지정해 별도 이미지를 만듭니다. 이 경우에만 `/adb_keys`와 TCP 시작 rc가 들어갑니다. 개인키 `adbkey`는 PC 밖으로 복사하지 않으며, 개인화한 이미지는 다시 공개하지 않습니다.

## 9. 업데이트 반복 플래그가 남은 경우

저장된 `upgrade_step=3` 또는 BCB의 `boot-recovery`가 남아 있으면 새 system을 기록해도 recovery로 돌아갈 수 있습니다. USB 콘솔 스크립트의 RAM 변경만으로 영구 해결되지 않습니다.

관측한 기존 상태는 env/misc가 각각 8MiB였고 env 안에 CRC 보호된 64KiB 사본 두 개가 있었습니다. 자기 기기에서 읽은 전체 사본을 PC에 `env-before.img`, `misc-before.img`로 보관한 다음:

```sh
python3 src/prepare_boot_flags.py /path/to/own-boot-state-backups
```

이 도구는 확인된 기존 상태에서만 `upgrade_step 3→1`과 두 CRC를 계산한 **env 앞 128KiB**, BCB를 비우는 **misc 앞 2KiB**를 별도 파일로 만듭니다. 예상 상태·CRC가 다르면 멈춥니다. 생성물과 plan JSON은 자기 기기 전용이며 공개하지 않습니다.

실제 반영은 UART/root 복구 접근 상태에서만 합니다. `boot-flags-plan.json`의 BeforeSha256을 현재 두 블록 장치의 전체 SHA-256과 비교하고, 블록 크기가 각각 8MiB이며 마운트된 파일시스템이 아닌지 확인합니다. 일치하는 경우 생성 파일을 기기로 전송해 **해당 앞부분만** 기록합니다.

```sh
# root 셸에서, 자신의 현재 블록 장치·Before 해시·입력 파일 해시 확인을 마친 경우만
dd if=/path/to/env-normal-prefix.bin of=/dev/block/env bs=65536 count=2 conv=notrunc
sync
# env 전체 SHA-256이 plan의 envAfterSha256과 일치하는지 확인 후 계속
dd if=/path/to/misc-clear-bcb.bin of=/dev/block/misc bs=2048 count=1 conv=notrunc
sync
# misc 전체 SHA-256이 plan의 miscAfterSha256과 일치하는지 확인
```

파일 경로와 해시는 자기 백업에서 얻은 값을 사용합니다. `saveenv`로 환경 전체를 새로 쓰거나 env/misc 전체를 0으로 지우는 방식이 아닙니다. 이 배포본은 초기화·부트 플래그 수정을 자동 실행하지 않습니다.

## 10. 완료 판정과 원복

USB의 콘솔 `aml_autoscript`가 꽂혀 있으면 매번 수동 콘솔로 멈출 수 있습니다. 정상 부팅 경로를 복구한 뒤 콘솔 USB를 제거하고 시험합니다.

```sh
getprop sys.boot_completed
getprop ro.build.version.release
getprop ro.build.version.sdk
getprop ro.boot.verifiedbootstate
getprop sys.bfx.audio_patch
getenforce
```

`1`, Android 12 계열/API 32, `green`, 오디오 `ready`, `Enforcing`을 확인합니다. root에서 system/vbmeta 블록 장치 전체 SHA-256도 ZIP의 이미지와 비교합니다. 홈 화면과 HDMI 소리는 실제 TV로 확인하고, USB를 뺀 완전 전원 분리·재연결을 별도로 시험합니다. 로고나 warm reboot만으로 설치 완료라고 하지 않습니다.

실패하면 UART로 부팅 단계와 오류를 보존합니다. 원래 system/vbmeta를 되돌리는 경우도 반드시 자기 기기의 검증된 한 쌍을 사용합니다. Android 12가 바꾼 userdata가 Android 9와 호환된다고 가정할 수 없으므로, system/vbmeta 원복만으로 전체 롤백을 보장하지 않습니다. 원래 전체 백업과 복구 경로가 필요한 이유입니다.
