# USB Wi-Fi와 TV 리모컨: 2026-10-31 수정

Android 9에서 Android 12.1로 판올림한 BFX-AT100에서 적용·확인한 연결 수정입니다. **이번 공개는 소스와 오프라인 빌드 도구입니다. 기존 r1 릴리스 ZIP에는 들어 있지 않습니다.** 개인화된 실행 중 시스템이나 userdata를 복제한 새 ROM은 배포하지 않습니다.

## 같은 날 추가한 순정 입력 경로

후속 실물 시험에서 GATT fallback만으로는 순정 음량·확인 동작을 충분히 유지하지 못했습니다. 최신 소스는 원본 ARM32 HID 드라이버가 확인되면 GATT 주입을 중지합니다. 부팅 후 60초가 지나 깨어난 BMM-BA03과 재연결도 계속 감시해 순정 경로로 전환합니다. [원본 모듈 가드·통합·확인 marker·rollback과 HDMI 음량 안내](tv-playback.md#1-순정-bmm-ba03-드라이버-경로)를 함께 적용해야 하며, 아래의 이전 GATT 시험을 순정 모듈 재연결 시험과 혼동하지 않습니다.

## 적용 대상과 유선랜의 차이

| 항목 | 확인한 대상 |
|---|---|
| 출발점 | BFX-AT100, Android 9 `PI.15.520.8-20200731`, 기존 정적 파티션 유지 |
| 실행 시스템 | PHH v416 ARM32/Binder64 Android 12.1, 기존 kernel/vendor/DTB 유지 |
| 커널 | `4.9.113-gd284ece-dirty`, 원본 빌드 `#71` |
| USB 무선랜 | RTL8821CU, `0bda:c820`; 설치 디스크 모드 `0bda:1a2b` |
| 실물 리모컨 | BMM-BA03 Bluetooth, PnP `005d:0004`, compact keyboard report `0x80` |

**유선랜은 하드웨어에 따라 별도 작업이 필요합니다.** 확인한 BFX-AT100의 내장 Ethernet에서 DHCP 통신이 됐다는 결과를 다른 셋톱·보드 리비전·USB 유선랜에 일반화하지 않습니다. MAC/PHY, MDIO, reset/clock/pinmux, Device Tree, 커널 드라이버, vendor 서비스와 DHCP 경로를 해당 하드웨어에 맞춰 확인해야 합니다. 자신의 DTB/vendor와 고유 MAC·보정 자료를 유지합니다. 이 USB Wi-Fi 패치가 유선랜 드라이버를 설치하거나 다른 보드의 Ethernet을 자동 지원하지는 않습니다.

USB 무선랜도 제품 이름만 같다고 적용하지 않습니다. 실제 USB ID, 칩셋, 커널 ABI가 다르면 별도 포팅이 필요합니다. 확인한 내장 무선 칩은 Bluetooth 전용이며, 이번 Wi-Fi 연결은 외장 USB 수신기로 구현했습니다.

## 사용자에게 보이는 동작

- 설정의 **USB Wi-Fi**가 기존 TV 설정과 같은 패널·방향키 포커스로 열립니다.
- 수신기가 없으면 **“USB Wi-Fi 수신기를 연결하세요”**를 표시합니다. USB 장치만 보이고 `wlan0`가 준비되지 않으면 지원/준비 상태를 안내합니다. USB 제조사 추정만으로 드라이버 지원을 확정하지 않습니다.
- 확인한 설치 디스크 모드에만 SCSI eject를 보내 무선 모드로 전환합니다. 임의의 USB 저장장치에는 명령을 보내지 않습니다.
- 주변 네트워크 검색 후 기존 TV의 연결·암호 입력 화면을 사용합니다. 자체 비밀번호 저장소나 비밀번호 로그를 만들지 않습니다.
- 숫자키 입력과 화면 키보드의 **완료(✓)** 이동을 보정했습니다. 유선이 기본 연결이어도 설정 중 Wi-Fi 연결 요청을 유지해 무선 연결을 시험할 수 있습니다.
- 드라이버 준비 후 Wi-Fi HAL을 다시 시작합니다. 저장된 Wi-Fi 켜짐 상태를 부팅 시 제한된 대기/재시도로 복원하고, Android Wi-Fi 저장소가 재연결을 담당합니다.
- BMM-BA03의 누락된 홈·방향키·OK·뒤로·숫자키만 해당 Bluetooth report에서 해석합니다. 일반 HID 리모컨을 모두 이 규칙으로 바꾸지 않으며, 다른 제품은 Android 표준 경로와 실물 입력으로 별도 확인합니다. 음성/consumer report는 이 키 보정에서 변경하지 않습니다.

## 실제 시험과 공개 재빌드의 구분

| 시험 | 현장 수정본의 결과 |
|---|---|
| 주변 AP 검색 | 2.4/5GHz 검색 결과 수신 |
| Wi-Fi 연결 | 서로 다른 두 네트워크에서 인증·DHCP·DNS·인터넷 검증 상태 확인 |
| 유선 제거 | Wi-Fi만으로 ADB·인터넷 통신 확인 |
| 완전 전원 부팅 | LAN 없이 전원 분리·재연결 후 저장된 Wi-Fi 자동 복귀, 시간 동기화 확인 |
| 리모컨 재연결 | 새 페어링 없이 홈·방향키·OK·뒤로 조작, 사용자가 실제 동작 확인 |
| 숫자/키보드 | 0–9 및 단독 0 입력, 완료 선택 시 키보드 닫힘·다음 화면 이동을 사용자가 확인 |
| USB 제거·재연결 | 같은 부팅에서 USB 재인식, 무선 재연결과 인증된 ADB 복귀 확인 |
| 네트워크 변경 | 변경된 무선 주소로 다시 연결, 사용자가 정상 동작 확인 |

무선랜을 빼거나 네트워크를 바꾸면 기존 TCP 연결이 끊기므로 **노트북의 scrcpy 조작 창은 닫힐 수 있습니다.** 이를 곧바로 셋톱 전원 꺼짐으로 판단하지 않습니다. 같은 부팅 유지·무선 복귀를 따로 확인했습니다. 이 시험 당시 별도 HDMI 표시 장치가 없어 수신기 미연결 안내의 실제 TV 표시는 직접 확인하지 못했습니다. 장시간 전체 앱 무오류나 모든 USB 수신기·리모컨 지원을 입증한 결과는 아닙니다.

공개 전에는 개인 경로와 진단 수신기를 제거한 소스로 APK 재빌드, Java 키/보안 방식 테스트, 기존 DEX·리소스 보존 및 서명 검사를 실행했습니다. 드라이버도 원본 소스에서 재컴파일해 **205개 import CRC 일치**, 실제 `core/rtw_cmd.o`와 원본 HID/USB/network 모듈의 **280/324/437개 공통 타입에서 배치 차이 0개**를 확인했습니다. 런타임 overlay의 의존성과 ELF runpath도 검사했습니다. **이 공개 재빌드를 셋톱에 다시 기록한 시험은 아닙니다.** 현장 설치본의 실물 결과와 공개 출력 파일의 해시를 혼동하지 않습니다.

## 소스 구성

| 경로 | 역할 |
|---|---|
| `src/tv-connectivity/source/` | TV 패널, Android 기본 암호 입력 연동, USB 모드 준비, 부팅 복원, BMM-BA03 키 보정 |
| `src/tv-connectivity/compile-stubs/` | 기존 APK 클래스에 대한 컴파일 전용 선언. 출력 DEX에 넣지 않음 |
| `src/tv-connectivity/build_tvsettings.py` | 정확한 입력 APK만 수용, 원본 코드·리소스 유지, 수정본과 상위 버전 rollback APK 생성 |
| `src/usb-wifi/build_driver.py`, `abi_types.py` | 원본 config·컴파일러 확인, 커널 헤더 조정, 모듈 빌드와 실제 타입 배치 비교 |
| `src/usb-wifi/bfx_wifi_abi_probe.c` | 확인한 커널의 export CRC를 읽는 고정 probe. 읽기 후 ENODEV로 종료 |
| `src/usb-wifi/build_runtime.py` | 로컬 HAL·supplicant·VNDK 입력 해시 확인, private runpath·shim 구성, overlay manifest 생성 |
| `src/usb-wifi/overlay/` | ABI 확인 후 드라이버 로드, HAL 시작 순서, STA 전용 supplicant 기본값 |
| `src/usb-wifi/reference-*.json` | 일반적인 빌드 식별 정보·심벌 CRC·입력 파일 해시. 사용자/기기 고유 값 아님 |

원본 OEM APK, HAL/VNDK 바이너리, 완성 `.ko`, 서명 키는 Git에 넣지 않았습니다. 소스는 공개하지만 해당 원본의 권리를 새로 부여하지는 않습니다. GPL probe와 외부 드라이버/커널은 각각의 라이선스를 따릅니다. [공개 범위](source-and-privacy.md)도 확인하세요.

새로 작성한 TV 연결 코드와 USB Wi-Fi 보조 도구는 각 소스 폴더의 MIT `LICENSE`로 제공합니다. GPL-2.0-only probe와 외부 원본의 예외는 [라이선스 범위](../src/usb-wifi/NOTICE.md)에 명시했습니다.

## 1. 자기 기기의 입력 준비

먼저 [원본 백업·설치 조건](distribution.md)을 확인합니다. 아래 명령의 `/local/`은 설명용 경로입니다. 빌드 명령은 기기에 접속하지 않습니다.

TV 설정은 자기 원본에서 읽은 `com.android.tv.settings` 1.0.6 APK를 사용합니다. 지원하는 원본 SHA-256은 `a0809d1280325da87cbeac69c2a98dd54ac21ed26cf9f34cb1a317fce5cb9d36`입니다. 이 입력에는 기존 공개 `prepare_tvsettings.py`의 FileProvider 충돌 보정을 적용하고 로컬에서 다시 서명합니다. 기존 호환 수정본 SHA-256 `5ade308905d3be7d8acbe3f60fbb000d887954450a87c370fa69735d90b644ea`도 수용합니다. **원본 SKB 시스템에 이 APK를 설치하는 도구가 아니며**, 자신의 GSI가 사용하는 platform/shared UID 서명·privileged 권한과 맞아야 합니다. 해시가 다르면 guard를 지우지 말고 별도 분석합니다.

USB 드라이버에는 자신의 원본 kernel config와 디버그 타입 정보가 남아 있는 원본 `hid-skbrm.ko`, `btusb.ko`, `aml_hardware_dmx.ko`가 필요합니다. config의 확인한 SHA-256은 `reference-target.json`에 있습니다. 해당 원본이 없거나 비교가 실패하면 이 타깃용 빌드를 진행할 수 없습니다.

외부 입력은 고정한 소스를 사용합니다.

- [커널 소스](https://github.com/khadas/linux/tree/d71236547be9b86d527de0f62c2092ec032fd0fa)
- [RTL8821CU 드라이버 소스](https://github.com/brektrou/rtl8821CU/tree/8c2226a74ae718439d56248bd2e44ccf717086d5)
- [원본 버전 GCC 6.3.1 도구](https://github.com/khadas/buildroot_toolchain_gcc_linux-x86_arm_gcc-linaro-6.3.1-2017.02-x86_64_arm-linux-gnueabihf/tree/32a934c7f728290fd4f08bf415d0cd451aaf4724)
- ARM32 Wi-Fi userspace 참고 자료: [Khadas Android 11 v241024](https://dl.khadas.com/products/vim3/firmware/android/vim3-android-11-32bit-v241024.img.xz). 로컬에서 Wi-Fi HAL·supplicant와 해당 VNDK30 의존성만 추출합니다. **다른 보드의 전체 펌웨어를 BFX에 플래시하지 않습니다.** DRM·키·vendor 전체를 가져오는 절차가 아닙니다.

각 고정 소스/아카이브 해시는 `reference-target.json`, 추출한 userspace 파일의 기대 해시는 `reference-userspace-sha256.json`에 있습니다. userspace 입력 폴더에는 `bfx-wifi-hal`(원본 `wifi-hal-a11`), `bfx-wpa-supplicant`(원본 `wpa_supplicant`), `libwifi-hal-aml.so`, `libkeystore-wifi-hidl.so`, `libkeystore-engine-wifi-hidl.so`를 준비하고 VNDK30 라이브러리는 별도 폴더에 둡니다. 추출 결과를 공개 Git에 추가하지 않습니다.

## 2. TV 설정 APK 빌드

Python 3.11+, Android SDK platform 35/build-tools 35.0.0, JDK 21을 사용했습니다. Windows에서도 SDK/JDK 경로를 인자로 지정할 수 있습니다.

```sh
python -m venv /local/venv-tv
/local/venv-tv/bin/pip install -r src/tv-connectivity/requirements.txt
/local/venv-tv/bin/python src/tv-connectivity/build_tvsettings.py \
  --base-apk /local/private/TvSettings.apk \
  --sdk /local/sdk --java-home /local/jdk \
  --platform-key /local/private/platform.pk8 \
  --platform-cert /local/private/platform.x509.pem \
  --out /local/output/tv-connectivity
```

키는 로컬에만 둡니다. 기본 versionCode는 1021이고 rollback은 1022입니다. 기존 설치본보다 큰 버전이 필요하면 `--version-code`를 지정합니다. `build-verification.json`을 확인하고 자신의 GSI platform 인증서와 비교합니다. 기존 서명·권한이 맞는 TV 설정 앱이 설치된 시스템에서만 인증된 ADB로 업데이트할 수 있습니다.

```sh
adb -s YOUR_AUTHORIZED_DEVICE install -r /local/output/tv-connectivity/TvSettings-connectivity.apk
```

문제가 있으면 같은 서명의 `TvSettings-connectivity-rollback.apk`로 되돌립니다. 이것은 APK 코드만 복원하며 무선 드라이버나 userdata를 복구하는 파일이 아닙니다. 최초 system 통합은 아래의 이미지 절차가 필요합니다.

## 3. USB 드라이버와 런타임 overlay 만들기

Linux/WSL에서 `make`, host C 도구, 고정 cross compiler, `patchelf`와 Python 의존성을 준비합니다. 커널과 드라이버는 **원본에서 푼 별도 작업 사본**을 사용합니다. 빌더는 그 사본의 config·헤더·진단 문자열 코드를 변경합니다. 출력 폴더는 아직 없어야 합니다.

```sh
python3 -m venv /local/venv-wifi
/local/venv-wifi/bin/pip install -r src/usb-wifi/requirements.txt
/local/venv-wifi/bin/python src/usb-wifi/build_driver.py \
  --kernel /local/work/kernel --driver /local/work/rtl8821CU \
  --original-config /local/private/kernel.config \
  --stock-hid /local/private/hid-skbrm.ko \
  --stock-usb /local/private/btusb.ko \
  --stock-network /local/private/aml_hardware_dmx.ko \
  --cross-compile /local/gcc/bin/arm-linux-gnueabihf- \
  --out /local/output/driver

/local/venv-wifi/bin/python src/usb-wifi/build_runtime.py \
  --driver-build /local/output/driver \
  --userspace /local/private/wifi-userspace \
  --vndk30 /local/private/vndk30 \
  --cross-compile /local/gcc/bin/arm-linux-gnueabihf- \
  --out /local/output/wifi-overlay
```

드라이버 빌드가 거부되거나 원본 config가 다르면 실기기 적용을 하지 않습니다. CRC가 맞아도 구조체/inline 함수 배치가 다를 수 있습니다. 실제 실패 조사에서 소스 트리의 새 `CONFIG_AMLOGIC_VMAP` 기본값 때문에 thread-info 접근이 달라지는 문제가 있었고, 전체 config 차이와 실제 command object의 DWARF 타입을 비교해 보정했습니다. `CONFIG_AMLOGIC_SLAB_TRACE`도 대상에 없는 새 기본값을 끕니다. 모듈의 CRC 바이트를 사후 변조하거나 `insmod -f`로 강제 로드하지 않습니다.

## 4. 자신의 오프라인 system에 통합

출력은 OTA ZIP이나 자동 플래셔가 아닙니다. `src/build_system.sh`가 이번 Wi-Fi overlay와 TV APK를 자동으로 합치지도 않습니다. 아래 통합은 현재 기기의 Android 12.1 system 복사본과 복구 경로가 있는 작업자를 위한 수동 단계입니다.

1. 기존 정상 system/vbmeta와 TV APK를 백업하고, 원본 boot/vendor/DTB/TEE는 유지합니다.
2. `overlay-manifest.json`의 `files` 대상 경로, mode, SELinux type에 따라 Wi-Fi overlay를 **마운트되지 않은 system 복사본**에 합칩니다. ext4의 `shared_blocks`/공유 inode를 처리하고 원래 파일을 덮어 다른 inode를 함께 손상시키지 않는 방식이 필요합니다. [기존 빌더](../src/build_system.sh)의 별도 복사본·주입 재읽기·ext4 검사 구조를 참고합니다.
3. 수정 TV APK는 `/system/priv-app`의 해당 TV 설정 앱으로 통합합니다. 기본 system APK의 platform 서명·shared UID·기존 privileged 권한 allowlist를 유지하고, 새 서비스에 필요한 Bluetooth 권한이 실제 부여되는지 확인합니다. 이 앱은 일반 사용자 앱으로 설치해서 동일하게 동작하는 구성이 아닙니다.
4. Android Wi-Fi feature 선언, 프레임워크 권한, USB 접근 허용, VINTF와 기존 HAL 서비스 중복을 확인합니다. init overlay는 이 PHH 기반의 `phhsu_daemon` 도메인을 사용하므로 다른 ROM에 복사해 SELinux를 permissive로 바꾸지 않습니다. 자기 ROM의 제한된 로더 도메인을 먼저 준비해야 합니다.
5. 기존 generic HAL/supplicant와 새 서비스가 동시에 같은 인터페이스를 차지하지 않도록 init 등록과 시작 순서를 확인합니다. 기본 supplicant 파일에는 `p2p_disabled=1`만 추가하고 저장된 네트워크·소유권을 보존합니다. `userdata`의 Wi-Fi 설정 파일을 이미지에 복사하지 않습니다.
6. 전체 ext4 검사, 주입 파일 재읽기 SHA-256, 새 system AVB와 기존 파티션 descriptor를 유지한 vbmeta 검증을 수행합니다. 그 후에만 [UART 설치·재읽기 검증](distribution.md)의 자기 기기 절차를 사용합니다. **r1의 CRC나 vbmeta를 새 system에 재사용하지 않습니다.**

## 설치 후 확인 순서

처음에는 LAN·UART 복구 경로를 유지하고 부팅 완료, driver 상태 `loaded`, HAL 시작, `wlan0`, TV 메뉴 검색과 비밀번호 입력을 각각 확인합니다. DHCP 주소만으로 인터넷 성공을 판정하지 않고 DNS·외부 통신·Android 검증 상태를 확인합니다. 이후 LAN 제거 → Wi-Fi 통신 → 완전 전원 부팅 → 저장 네트워크 자동 복귀 → USB 제거/재연결 → 리모컨 키와 숫자키 순서로 시험합니다. BMM-BA03 보정은 이미 페어링된 해당 모델만 선택하며 페어링 정보는 배포하지 않습니다.

개인 Wi-Fi 암호·Google 계정·ADB 키·Bluetooth 주소·장치 serial을 테스트 결과나 Git에 넣지 않습니다. APK rollback과 원래 system/vbmeta 복원 경로를 각각 유지합니다. 미확인 칩셋이나 다른 보드에는 성공 사례만 보고 같은 모듈을 적용하지 않습니다.
