# 호환성 수정과 실제 검증 범위

초기 현장 수정본, 공개 r1 재빌드, 후속 개인화 R3는 서로 다른 이미지입니다. 최신 측정 결과와 배포본 구분은 [R3 검증 기록](runtime-validation.md)이 우선합니다.

## 화면: TV SystemUI와 휴대폰 Keyguard 충돌

vanilla GSI는 완전한 제조사 Android TV 제품 이미지가 아닙니다. TV 자원 선택으로 TvStatusBar가 시작되는 환경에서 휴대폰 KeyguardService가 phone StatusBar를 가정해 null을 참조했습니다. 관측 기기에서는 해당 KeyguardService 구성요소를 사용자 단위로 비활성화한 뒤 framework를 재시작해 화면을 복구했습니다.

```text
com.android.systemui/com.android.systemui.keyguard.KeyguardService
```

이것은 기기 호환성 조정이며 일반 휴대폰에 적용할 설정이 아닙니다. TV 설정 APK의 FileProvider 충돌은 authority와 그 DEX 참조를 같은 길이로 바꾸고 DEX 무결성을 다시 계산해 처리했습니다. 공개 소스 `prepare_tvsettings.py`는 그 보조 코드이며 APK와 서명 키는 포함하지 않습니다. 런처·TV 설정 구성은 vanilla 기반 설치 후 별도 작업입니다.

## 부팅: 고정 IP 저장 파일의 읽기 오류

초기에 노트북 직결용 고정 IP를 저장한 뒤 다음 부팅에서 EthernetService가 반복 종료됐습니다. 이는 작업 중 추가한 설정에서 발생한 문제였습니다.

```text
IpConfigStore.readIpConfigurations
NullPointerException: LinkAddress.getAddress() on null
EthernetService.onBootPhase
```

저장 파일의 gateway 레코드와 현재 reader가 맞지 않았습니다. 해당 파일을 백업한 뒤 이름을 변경해 DHCP 기본값으로 복구했고, 재부팅과 USB 없는 전원 부팅으로 확인했습니다. 공개한 `BfxEthernetConfig.java`는 **읽기 전용**이며 인자가 있으면 서비스 호출 전에 종료합니다. 현재 구성에서는 Android 고정 IP 저장 기능을 사용하지 않습니다.

## 부팅 애니메이션

PHH `libbootanimation.so`에서 사용할 애니메이션 ZIP이 없어 mAnimation이 null인데 화면 배율 블록에서 역참조했습니다. 6바이트 분기 수정으로 null일 때 그 블록만 건너뛰어 기본 Android 애니메이션 경로를 유지했습니다. 애니메이션 전체를 끈 것이 아닙니다.

## 오디오 HAL

기존 Amlogic `audio.primary.amlogic.so`의 출력 스트림 생성 오류 경로가 해제 뒤 성공 처리로 흘러 `get_sink_format`에서 잘못된 포인터를 사용했습니다. 14바이트 수정으로 오류 경로에서 출력 포인터를 비우고 -EINVAL로 반환하도록 했습니다. 성공 경로는 유지했습니다.

수정한 라이브러리는 system 안에 두고 vendor HAL 시작 전 bind mount했습니다. 원래 vendor 파티션을 다시 쓰지 않았습니다. 초기 임시 HAL 재시작에서는 HDMI 재등록이 필요했지만, 부팅 초기에 수정본을 적용한 이후 재부팅/완전 전원 시험에서는 자동 HDMI 출력과 실제 TV 소리를 확인했습니다.

`src/patch_libraries.py`는 **확인한 원본 전체 SHA-256, 크기와 원래 바이트가 전부 일치할 때만** 별도 파일을 만듭니다. 수정 라이브러리 자체는 Git 소스에 넣지 않지만 배포 system 이미지에는 포함됩니다. 현장 이미지의 개인 serial 조건은 공개 r1에서 모델명과 정확한 라이브러리 해시 조건으로 대체했습니다. 실제 기기 serial은 포함하지 않습니다.

## 장시간 kernel wakelock 통계 읽기 고착

후속 R2 현장 이미지에서 `KernelWakelockReader`의 파일 읽기가 멈춰 `BatteryStatsImpl` 잠금, Watchdog의 system_server 종료와 정상 재부팅 고착으로 이어졌습니다. R3에는 legacy 통계 파일의 읽기 뷰만 대체하는 보정을 적용했습니다. 실제 wake-lock/suspend 제어는 바꾸지 않지만 개별 legacy 통계는 생략됩니다. 커널 내부 락까지 특정해 수정한 작업은 아닙니다.

현재 main 빌더에 `overlay/bfx-wakelock-stats-compat.sh`, `.rc`, `wakeup_sources-safe.txt`를 통합했습니다. 공개 r1 ZIP에는 이 보정이 없고 r1 자체의 장시간 재현 시험도 하지 않았습니다. R3에서 실제 mount와 60분·61회 수집, 정상 재부팅 2회를 확인했습니다. [수정 범위·시험·남은 한계](runtime-validation.md)를 참고하세요.

## 초기 현장 수정본의 검증 이력

아래 표는 후속 Google 통합/R3 이전의 기록입니다. R3에서 새로 한 전원 부팅·실제 TV 청취 시험으로 재사용하지 않습니다.

| 항목 | 확인 범위 |
|---|---|
| Android 9 → 12 계열 적용 | Android 12.1/API 32 속성 및 실제 부팅 완료 |
| 자동 부팅 | USB 없는 완전 전원 분리·재연결 성공 |
| 화면 | 실제 TV에서 홈/설정 표시 확인 |
| 소리 | 48kHz PCM 시험음의 실제 TV 출력 확인 |
| 유선 인터넷 | DHCP, 외부 IP·DNS 통신 확인 |
| 시간 | 한국 시간 동기화 확인 |
| ADB | 승인된 PC의 인증 연결 확인 |
| Verified Boot / SELinux | 수정 이미지에서 green / Enforcing 확인 |
| Google 서비스 | 당시 프레임워크·시스템 권한 불일치. 이후 개인화 R3의 통합·유지 확인은 별도 기록 |
| Wi-Fi | 사용 가능한 Wi-Fi 장치 미확인; 확인한 CYW20706은 Bluetooth 전용 |
| DRM·OTT | 인증·실제 재생·보안 수준 보장 안 함 |
| 장시간 안정성 | 이 초기 단계에서는 미검증. 후속 R3는 60분·61회 및 재부팅 2회 확인; 전체 코덱·장기 무오류 보장 아님 |

최초 수정 후 특정 시험에서 crash 버퍼가 비어 있었다는 결과를 모든 앱·전체 세션 무오류로 확대하지 않습니다. 특히 이후 응용 프로그램 시험에서는 AudioFlinger 시간 초과가 별도로 한 번 관측됐습니다. 기존 SIGSEGV 경로 수정과 모든 오디오 문제 해결은 같은 주장이 아닙니다.
