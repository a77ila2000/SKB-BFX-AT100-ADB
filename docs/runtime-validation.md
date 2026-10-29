# 후속 R3: 장시간 고착 보정과 Google·DRM 검증

확인일: **2026-10-29**. Android 9에서 판올림한 동일 BFX-AT100의 **개인화 현장 이미지 R3**에서 얻은 결과입니다. 기존 공개 `r1` ZIP을 시험한 결과가 아닙니다.

## 공개 배포본과 현장 이미지 구분

| 항목 | 공개 r1 ZIP | 후속 현장 R3 | 현재 main 소스로 새로 빌드 |
|---|---|---|---|
| 기반 | PHH v416 vanilla, Android 12.1/API 32 | 같은 기반에 현장 구성 추가 | PHH v416 vanilla |
| wakelock 통계 읽기 보정 | 미포함 | 적용·실기 검증 | 보정 소스 포함 |
| Google 앱·로그인 | 미포함 | 시스템 통합·계정 유지 확인 | Google 앱 미포함 |
| PHH su | 기반 개발용 구성 포함 | 앱용 su·루트 데몬 제거 | 기반 개발용 구성 유지 |
| 사전 승인 PC | 없음 | 소유자 PC 구성 포함, 비공개 | 기본 없음. 로컬 공개키 옵션만 제공 |
| 60분·61회와 재부팅 2회 | 이 ZIP에서는 미시험 | 아래 범위 통과 | 별도 재빌드·검증 필요 |

**R3 개인 이미지는 배포하지 않습니다.** 공개 r1 ZIP의 내용·해시는 이 문서나 main 소스 변경만으로 갱신되지 않습니다. 기존 ZIP에 R3의 Google·DRM·장시간 시험 결과를 적용하지 않습니다.

## 발견한 장시간 고착

후속 R2 현장 이미지에서는 약 30분 뒤 배터리 통계 작업이 멈췄습니다. ANR의 호출 경로는 다음과 같았습니다.

```text
Linux.readBytes / FileInputStream.read
  KernelWakelockReader.readKernelWakelockStats
  BatteryStatsImpl.updateKernelWakelocksLocked
  BatteryExternalStatsWorker.updateExternalStatsLocked
```

작업 스레드가 `BatteryStatsImpl` 잠금을 가진 채 커널 CPU를 계속 사용했고, Watchdog가 system_server를 종료해도 해당 스레드가 남았습니다. 정상 framework 재시작과 소프트웨어 재부팅도 완료되지 않았습니다. `sys.boot_completed=1`과 ADB 연결은 이때도 남아 있어 정상 동작의 충분한 증거가 아니었습니다.

이 기기의 Android 12 reader는 `/proc/wakelocks`가 없으면 `/d/wakeup_sources`를 읽습니다. `/d`는 `/sys/kernel/debug`입니다. ANR과 실제 파일 존재 여부로 구형 커널 통계 읽기 경로를 확인했지만, **커널 내부의 정확한 함수·락까지 특정한 근본 수정은 아닙니다.** Netflix나 DRM이 최초 원인이라고 단정하지 않습니다.

## 공개한 호환성 보정

- [bfx-wakelock-stats-compat.sh](../overlay/bfx-wakelock-stats-compat.sh): 모델을 확인하고 통계 파일 위에 헤더 파일을 bind mount합니다. 실제 mountinfo를 확인한 뒤에만 `sys.bfx.wakelock_stats_compat=ready`를 기록합니다.
- [bfx-wakelock-stats-compat.rc](../overlay/bfx-wakelock-stats-compat.rc): 부팅 초기와 부팅 완료에 멱등 실행합니다.
- [wakeup_sources-safe.txt](../overlay/wakeup_sources-safe.txt): 대체 통계 헤더입니다.

실제 wake-lock 획득·해제, wakeup_count와 suspend 제어를 바꾸지는 않습니다. **대신 legacy 커널의 개별 wake-lock 통계가 생략됩니다.** 전체 배터리 통계가 원본과 동일하다는 의미는 아닙니다.

[현재 빌더](../src/build_system.sh)는 세 파일을 새 system 이미지에 넣고 SELinux 라벨·재읽기·ext4·AVB 검증을 수행합니다. 원본 system과 서명이 맞는 vbmeta를 함께 새로 구성해야 합니다. 이 파일만 실행 중인 system에 복사하거나 r1 ZIP에 단순 추가하면 되는 OTA 방식이 아닙니다. 구형 커널의 원래 raw 통계 파일을 반복해서 직접 읽는 재현 시험은 기기를 고착시킬 수 있으므로 하지 않습니다.

## 실제 R3 검증 결과

| 검사 | 관측 결과 |
|---|---|
| 기록 전후 | 기존 system/vbmeta 전체 CRC 확인, 변경 후 전체 readback CRC 일치 |
| 같은 부팅에서 연속 검사 | **3,600.92초, 61회 통과** |
| 예기치 않은 재부팅·system_server 교체 | 0회 |
| 배터리 통계 수집 | 중앙값 0.14초, 최장 0.172초 |
| 가용 메모리 | 약 1.37–1.89 GiB |
| 정상 재부팅 | 2회, 서로 다른 boot ID로 복귀, UART 입력 0바이트 |
| 재부팅 뒤 통계 보정 | 실제 read-only mount와 각 부팅에서 3회 통계 수집 확인 |
| Google | 시스템 앱·권한 통합, 계정과 로그인 구성 유지, Play 스토어 동작 확인 |
| ADB·홈 | 인증된 ADB와 기본 홈 유지, 앱용 su 부재, SELinux Enforcing |
| Widevine | L1 기본 세션 생성, securityLevel 5, 정상 종료 및 재부팅 후 유지 |
| PCM | 재부팅 후 48kHz 스테레오 48,000프레임 완료, HDMI 출력 경로 확인 |
| 첫 R3 부팅의 앱·입력 | 스토어·Netflix Activity 시작, 설정↔홈 5회 왕복, 방향키 30회 포커스 이동 |
| 마지막 읽기 점검 | 새 crash·ANR 없음, 기본 홈 포커스, 임시 진단 앱 제거 |

40회 중간 검사도 통과했으며 최종 관찰 범위는 61회입니다. crash 버퍼만 보지 않고 실제 Binder 응답, 프로세스 상태·PID 유지, boot ID와 통계 수집 완료를 함께 확인했습니다. 정상 재부팅은 완전한 전원 분리·재연결 시험과 다릅니다. 초기 현장 이미지에서 확인했던 USB 없는 전원 부팅·실제 TV 소리를 R3의 새 시험으로 재사용하지 않았습니다.

## Google·Netflix에서 확인한 범위

현장 R3는 Google 서비스·필요 권한을 시스템에 통합했습니다. GSF의 PendingIntent 오류는 해당 패키지 버전의 호환성 조건으로 제한해 보정했습니다. Google APK나 로그인 데이터는 저장소·배포 ZIP에 넣지 않습니다.

기존 기기의 MediaDrm provisioning 요청·응답을 정식 HTTPS 경로로 처리한 뒤 L1 세션이 열렸습니다. **다른 기기의 DRM 키를 추출·복사·교체하거나 제조사 인증을 위장한 작업이 아닙니다.** 원본 vendor/TEE/보안 키 영역을 플래시하지 않았습니다.

원본 동일 모델의 Netflix 기능 선언을 복원하자 스토어의 호환 불가 표시가 사라졌고 **Netflix TV 13.2.2 build 27249**로 Play 스토어 업데이트와 Activity 시작을 확인했습니다. 보안 Surface는 원격 캡처에서 검게 보였으며 보호를 우회하지 않았습니다. **설치·실행 및 DRM 세션 생성은 실제 TV 로그인·구독 콘텐츠 재생 성공과 구분합니다.**

## 남은 한계

- 실제 TV의 Netflix 로그인·구독 재생, HDCP·최대 해상도, R3의 완전 전원 부팅, 실제 마이크·OK Google은 미검증입니다.
- Cast의 HDMI_CEC privileged 권한 부족은 남아 있습니다. 쿠팡플레이의 별도 보안 거부도 해결했다고 보고하지 않습니다.
- 두 번째 재부팅 뒤 추가 앱 재실행·리모컨 전환 시험은 자동 승인 검토가 차단해 실행하지 못했습니다. 첫 부팅의 실제 UI 시험과 최종 읽기 점검을 이 추가 시험의 통과로 대체하지 않았습니다.
- 일부 GPU 완료 시각은 LONG_MAX로 기록돼 지연 통계를 왜곡했습니다. 통제한 설정 화면의 유효 120프레임 중앙값은 14.94ms였지만 전체 동작의 60fps를 보장하지 않습니다.
- 60분과 재부팅 2회에서 기존 고착이 재현되지 않았다는 결과이며 장기 무오류·전체 앱 호환성·제조사 인증의 증거는 아닙니다.

여기에는 측정 요약과 개인정보가 없는 보정 소스만 공개합니다. 계정명·키·주소·boot UUID·원본 로그·개인 화면·개인화 이미지는 제외했습니다.
