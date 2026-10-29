# Android 9 → Android 12.1: 설치 구조와 재현 범위

이 문서는 한 대의 BFX-AT100에서 수행한 작업의 구조를 설명합니다. 단순 설정 초기화나 기존 Android 12의 재설치가 아니라, **Android 9 기기에 새 Android 12 계열 system을 적용한 포팅**입니다. 전용 복구 자료와 UART 접근을 확보한 다음 단계별로 검증했으며 범용 원클릭 설치기는 아닙니다.

## 1. 기기와 복구 자료 확인

- 정확한 모델·기판·부팅 파티션·eMMC 용량을 먼저 읽었습니다.
- eMMC user area와 boot0/boot1을 별도 저장하고 원본 읽기 해시와 PC 재읽기 해시를 비교했습니다. RPMB는 백업 범위 밖입니다.
- 32비트 BusyBox `dd`의 큰 seek가 4GiB에서 반복되는 문제를 발견했습니다. 단순 조각별 일치만으로 백업 완료라고 하지 않았고, 64비트 `pread` 보조 코드와 순차 전송·전체 해시로 다시 확인했습니다. 공개한 `src/read-range64.c`는 이 읽기 전용 보조 코드입니다.
- 개인 기기 덤프와 UART 전체 로그는 공개하지 않습니다.

## 2. GSI 선택

사용한 기반은 [PHH v416](https://github.com/phhusson/treble_experimentations/releases/tag/v416)의 `system-squeak-arm32_binder64-ab-vanilla.img`입니다. 실제 userspace는 ARM32, Binder 프로토콜은 8(Binder64)이었습니다. CPU가 64비트를 지원한다는 사실만으로 ARM64 이미지를 선택하지 않았습니다.

v416은 Android 12.1/API 32, 보안 패치 2022-07-05입니다. 분석한 SKB 공식 Android 12/API 31 OTA와는 다른 시스템입니다. GSI 파일명의 `ab`도 현재 장치가 A/B OTA 방식으로 전환됐다는 뜻으로 해석하지 않습니다.

## 3. 기존 구조를 유지한 system 구성

구형 kernel 4.9.113, vendor, DTB와 개별 정적 파티션 구조를 유지했습니다. system은 기존 크기 **1,551,892,480바이트**, vbmeta는 **2,097,152바이트**에 맞췄습니다. super를 새로 만들거나 전체 기기를 최신 SKB 파티션 구조로 재분할하지 않았습니다.

`overlay/fstab.bfx_gsi`에서 원래 vendor/odm을 first stage에 연결하고 vendor AVB를 유지합니다. 기존 작은 product 파티션이 GSI 내부의 product/system_ext를 가리지 않도록 product의 별도 마운트는 제외했습니다.

검증한 부팅 인자는 다음과 같습니다. 이 이름과 장치 경로는 관측 기기의 값이며 다른 기기에 임의 적용하면 안 됩니다.

```text
androidboot.android_dt_dir=/proc/device-tree/firmware/bfx_gsi/
androidboot.fstab_suffix=bfx_gsi
androidboot.boot_devices=ffe07000.emmc
```

처음 진단에는 shell 사용자 UART console과 인증된 ADB를 사용했습니다. 작업 PC의 공개 ADB 키를 현장 이미지에 넣었던 사본은 개인화 자료로 분류해 공개하지 않습니다. 공개 빌더는 선택한 로컬 공개 키만 입력으로 받을 수 있고, 무인증 ADB를 켜지 않습니다.

## 4. AVB 메타데이터

원래 vbmeta와 GSI가 같은 공개 AOSP 시험 키를 사용한다는 것을 확인한 뒤, system descriptor와 root dm-verity 명령줄만 새 이미지에 맞춰 만들었습니다. boot/recovery/vendor/product/dtbo/dtb의 기존 descriptor는 바이트 단위로 보존했습니다. root flags=0, rollback index=0을 유지했으며, GSI의 큰 rollback 값을 무작정 가져오지 않았습니다.

오프라인에서는 system hashtree와 서명, root vbmeta와 변경하지 않은 6개 파티션까지 연결 검증했습니다. 실제 부트로더에서도 AVB 검증 성공을 확인했습니다. 이 결과는 관측 장치의 시험 키 수용 조건에 한정됩니다. 보안 부팅 전체를 해제했다거나 제조사 서명을 만들었다는 의미가 아닙니다.

## 5. 기록과 재읽기

초기 설치는 내부 Android 파일시스템이 마운트되지 않은 복구 환경에서 system/vbmeta만 기록했습니다. 이후 부팅·오디오 수정본은 U-Boot의 지원 명령을 확인하고 동일한 두 파티션에 적용했습니다. 각 기록 뒤 전체 파티션을 다시 읽어 CRC32 또는 SHA-256을 비교했고 Android에서도 전체 SHA-256을 대조했습니다.

단순 명령 완료 메시지나 로고만으로 성공이라고 하지 않았습니다. 공개 소스는 이미지 생성·검증까지만 하며, 어떤 블록 장치를 자동으로 찾아 기록하거나 erase/saveenv/공장 초기화를 수행하지 않습니다.

## 6. 처음 부팅과 호환성 수정

first-stage init → vendor dm-verity → split SELinux policy → APEX → Android 서비스 → 부팅 완료를 확인했습니다. 처음에는 TV/휴대폰 SystemUI 조합의 Keyguard 충돌과 예전 Google 앱 권한 문제로 검은 화면이 있었고, 해당 구성요소를 복구 가능한 사용자 단위 비활성화 방식으로 조정했습니다. 관련 변경과 남은 한계는 [호환성 기록](compatibility.md)에 있습니다.

## 7. 최종 확인

USB를 제거하고 전원을 완전히 분리했다가 다시 연결해 자동 부팅을 확인했습니다. 실제 TV 화면, 인증된 ADB, DHCP 유선 연결, 시간 동기화와 PCM HDMI 소리를 확인했습니다. warm reboot나 USB RAM 부팅만으로 독립 부팅 성공을 주장하지 않습니다.

## 재현할 때 필요한 개인 자료

자기 기기의 원본 이미지·검증 해시·서명 수용 조건·복구 경로가 필요합니다. 이 저장소에 없는 제조사 blob, 개인화 키 또는 eMMC 사본을 임의의 다른 기기 자료로 대체하면 안 됩니다. system/vbmeta만 원복해도 Android 12가 변경한 userdata까지 Android 9와 호환되는 것은 아니며, 전체 롤백에는 원래 백업의 범위와 검증이 필요합니다.
