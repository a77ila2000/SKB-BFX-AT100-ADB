echo BFX_UART_CONSOLE_BEGIN
setenv upgrade_step 1
setenv reboot_mode_android normal
setenv boot_part boot
setenv update 'echo BFX_SKIP_UPDATE'
setenv recovery_from_flash 'echo BFX_SKIP_FLASH_RECOVERY'
setenv recovery_from_udisk 'echo BFX_SKIP_USB_RECOVERY'
setenv recovery_from_sdcard 'echo BFX_SKIP_SD_RECOVERY'
setenv switch_bootmode 'echo BFX_SKIP_SWITCH_BOOTMODE'
setenv upgrade_key 'echo BFX_SKIP_UPGRADE_KEY'
setenv bootdelay -1
setenv bootretry -1
setenv bootcmd 'echo BFX_MANUAL_BOOT_ONLY'
setenv altbootcmd 'echo BFX_MANUAL_ALTBOOT_ONLY'
setenv failbootcmd 'echo BFX_MANUAL_FAILBOOT_ONLY'
setenv menucmd 'echo BFX_MANUAL_MENU_ONLY'
printenv bootcmd bootdelay bootretry update recovery_from_flash switch_bootmode bcb_cmd
echo BFX_UART_CONSOLE_READY
