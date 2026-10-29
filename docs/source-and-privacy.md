# 공개 소스 사용법과 개인정보 제외

## 공개한 것

| 경로 | 역할 |
|---|---|
| `src/build_system.sh` | 로컬 원본 GSI의 복사본에 fstab·오디오 호환성 파일을 넣고 AVB를 재구성하는 오프라인 빌더 |
| `src/build_vbmeta.py` | 기존 descriptor를 보존하면서 새 system descriptor/root dm-verity 명령줄 구성 |
| `src/patch_libraries.py` | 정확한 원본 해시를 요구하는 bootanimation·오디오 오류 경로 패치 |
| `src/read-range64.c` | 4GiB 이상 오프셋을 읽는 ARM32용 읽기 전용 보조 코드 |
| `src/binder-version.c` | 포인터 크기와 Binder 프로토콜 읽기 |
| `src/BfxEthernetConfig.java` | Ethernet 설정 읽기 전용 진단 |
| `src/prepare_tvsettings.py` | TV 설정 APK의 FileProvider authority 충돌 수정 |
| `src/serial-terminal.ps1` | RX 기본 UART 터미널, 명시적 TX와 자체 검사 |
| `src/check_release.py` | 배포 이미지 해시·원본 vbmeta·유지할 원본 파티션의 AVB 연결 검증 |
| `src/prepare_boot_flags.py` | 자기 env/misc 백업에서 확인된 업데이트 반복 플래그 변경만 오프라인 준비 |
| `src/uboot-console.cmd`, `src/make_usb_script.py` | flash 쓰기가 없는 RAM 전용 USB 콘솔 진입 스크립트와 uImage 생성 |
| `overlay/` | 장치별 fstab과 부팅 초기 오디오 bind mount 구성 |
| `tests/test_sources.py` | 패치 가드·파일 범위와 64비트 읽기 회귀 검사 |

현장 작업 코드에서 개인 경로·주소·기기 식별값을 제거한 **공개용 소스**입니다. 공개 빌더는 ADB 키와 장치 serial을 기본 포함하지 않고 ADB 인증을 켭니다. 개인화 현장 이미지와 배포본의 바이트/해시는 다릅니다. 소스 공개는 전체 Android 소스를 처음부터 빌드한 자체 ROM이라는 의미가 아닙니다. 완성 배포 ZIP과 사용 방법은 [배포 안내](distribution.md)에 있습니다.

## 로컬에 따로 필요한 자료

- 자신이 확보하고 검증한 PHH v416 ARM32/Binder64 vanilla 이미지와 원래 기기의 vbmeta/vendor 자료.
- 원래 vendor에서 읽은 정확한 `audio.primary.amlogic.so`.
- [AOSP Android 12 avbtool](https://android.googlesource.com/platform/external/avb/+/refs/tags/android-12.0.0_r34/avbtool.py).
- 관측한 서명 조건에 맞는 키. 현장에서는 AOSP에 공개된 시험용 fixture를 사용했으며, 실제 개인 키를 저장소에 올리지 않습니다. [AOSP 시험 fixture 위치](https://android.googlesource.com/platform/external/avb/+/refs/tags/android-12.0.0_r34/test/data/)
- Python 3, OpenSSL, `debugfs`, `e2fsck`, `sha256sum`, `truncate`; Linux/WSL 작업 환경.

## 오프라인 빌드 예시

아래 이름은 설명용이며 실제 개인 경로나 식별값이 아닙니다. avbtool은 pinned Android 12 버전을 사용합니다. 이 명령은 이미지만 만들고 기기에 쓰지 않습니다.

```sh
export AVBTOOL=/local/tools/avbtool.py
export SIGNING_KEY=/local/private/accepted-key.pem
export STOCK_VBMETA=/local/private/original-vbmeta.img
export STOCK_PARTS_DIR=/local/private/verified-original-partitions
export AUDIO_LIBRARY=/local/private/audio.primary.amlogic.so

bash src/build_system.sh /local/input/system-squeak-arm32_binder64-ab-vanilla.img /local/output/bfx12
```

기본 빌드에는 기기 시리얼과 PC 키가 없습니다. 자기 PC를 미리 등록하려는 경우에만 `export ADB_PUBLIC_KEY=/local/private/adbkey.pub`를 추가합니다. 이때 인증을 유지하면서 해당 공개키와 TCP ADB 시작 rc를 넣습니다. private key는 입력하지 않으며, 이 옵션으로 만든 개인화 이미지는 다시 공개하지 않습니다. 자신의 키를 빼려면 깨끗한 원본 GSI에서 이 변수를 비우고 새 출력 폴더로 다시 빌드합니다.

빌더가 성공해도 flash 설치 승인이나 기기 호환성 검증을 대신하지 않습니다. `docs/install.md`의 원본 백업·파티션 확인·검증 절차가 필요합니다.

## 소스 검사

```sh
python3 -m unittest discover -s tests -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -File src/serial-terminal.ps1 -SelfTest
```

2026-10-29 공개 전 검사에서 Python 회귀 검사 6개, C 컴파일 검사, shell 문법 검사, UART 자체 검사가 통과했습니다. 공개 빌더를 실제 로컬 원본 자료로 실행해 두 라이브러리 패치의 예상 해시, 주입 파일의 재읽기 일치, ext4 검사, system AVB 및 기존 6개 파티션을 포함한 root vbmeta 검증까지 통과했습니다. ZIP의 압축 무결성 및 내부 이미지 해시도 확인했습니다. 새 모델 기반 오디오 가드는 기존 설치본에서 실행해 ready를 확인했지만, 배포 이미지를 기기에 새로 기록한 것은 아니며 현장 개인화 이미지의 부팅·소리 검증과는 구분합니다.

UART 사용 시 현재 PC의 실제 COM 포트를 지정합니다. 기본은 RX 전용이고 VCC는 연결하지 않습니다. TX는 로직 전압과 프롬프트를 확인한 뒤 명시적으로 사용합니다. 자체 검사는 포트를 열지 않습니다.

## 제외한 것

기기 serial/CID/MAC/UUID, 실제 IP·라우터·서버 접속 정보, 사용자 이름·PC 경로, ADB 공개/비공개 키, 비밀번호·토큰·인증서/개인 키 파일, 전체 UART 로그·화면 캡처, eMMC/파티션 덤프, 제조사 OTA·APK 원본, 게임·에뮬레이터 자료를 제외했습니다. 라이브러리 원본 파일을 따로 배포하지는 않지만, 필요한 수정 오디오 라이브러리는 배포 system 안에 들어 있습니다.

기존 ADB 문서의 고정 메뉴 번호·펌웨어 버전·공개된 ADB 메뉴 PIN은 개인 계정 비밀번호와 구분합니다. 예전 안내는 SKB 원본 펌웨어의 분석 기록이며, 새 vanilla GSI의 설정 절차로 해석하지 않습니다.

`.gitignore`는 공개할 텍스트 소스 폴더만 허용합니다. 설치용 ZIP은 Git blob이 아닌 Releases 첨부 파일로 올립니다. 이미지 전체에서 작성자의 알려진 식별값·실제 PC ADB 키와 금지 경로 부재를 검사하고, ZIP 안의 이미지 해시 및 업로드된 첨부 파일의 SHA-256을 확인합니다. GitHub 소스 tree도 로컬 공개 파일의 Git blob 해시와 대조합니다.
