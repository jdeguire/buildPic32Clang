/* watchdog.c

   This test sets up the device configuration registers. Previous testing suggests that we need to
   set up most of them for the device to run. Oddly enough, setting up none of them makes the
   Microchip tools use useful defaults. I never did figure out which register was the one that I
   needed to make the device run, but really we should probably just program them all anyway.

   We need a test that we can see, so let's enable the watchdog timer and let it trip. That will
   reset the CPU periodically and we can see that happen by seeing an LED blink.

   This is running on a PIC32CZ CA80 Curiosity Ultra board, which has a PIC32CZ8110CA80208 device
   on it. If you want to build this on a different device, substitute the name of your device in
   the below command where you see the device name.

   Build this file with 'path/to/clang --config pic32cz8110ca80208.cfg -o watchdog.elf watchdog.c'
   Make it an Intel Hex file with 'path/to/llvm-objcopy -O ihex watchdog.elf watchdog.hex'
   */

#include <which_pic32.h>
#include <stdint.h>
#include <stdbool.h>

#ifndef __PIC32C
#  warning This was tested on a PIC32C device only.
#endif

/* Most of these are set to their factory defaults as given in Section 11.4 of the datasheet.
   The exception is USERCFGn_FUCFG0 because that controls the watchdog timer. */
const uint32_t FUSES_BOOTCFG1_BLDRCFG = 0xC0000000;
const uint32_t FUSES_BOOTCFG2_BLDRCFG = 0xC0000000;

const uint32_t FUSES_BOOTCFG1_BROM_BSEQ = 0xFFFE0001;
const uint32_t FUSES_BOOTCFG2_BROM_BSEQ = 0xFFFF0000;

const uint32_t FUSES_BOOTCFG1_BFM_CHK_TABLEPTR = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_BFM_CHK_TABLEPTR = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_KEYVAL_TZ0_CE_ALL0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_TZ0_CE_ALL1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_TZ0_CE_ALL2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_TZ0_CE_ALL3 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_TZ0_CE_ALL0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_TZ0_CE_ALL1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_TZ0_CE_ALL2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_TZ0_CE_ALL3 = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_CELOCK_TZ0_CE_ALL0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_CELOCK_TZ0_CE_ALL1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_CELOCK_TZ0_CE_ALL2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_CELOCK_TZ0_CE_ALL3 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_CELOCK_TZ0_CE_ALL0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_CELOCK_TZ0_CE_ALL1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_CELOCK_TZ0_CE_ALL2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_CELOCK_TZ0_CE_ALL3 = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_KEYVAL_CRCCMD0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_CRCCMD1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_CRCCMD2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_CRCCMD3 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_CRCCMD0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_CRCCMD1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_CRCCMD2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_CRCCMD3 = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_KEYVAL_HOSTDALELEV0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_HOSTDALELEV1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_HOSTDALELEV2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYVAL_HOSTDALELEV3 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_HOSTDALELEV0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_HOSTDALELEV1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_HOSTDALELEV2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYVAL_HOSTDALELEV3 = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_KEYCONFIG_HOSTDALELEV0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYCONFIG_HOSTDALELEV1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYCONFIG_HOSTDALELEV2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_KEYCONFIG_HOSTDALELEV3 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYCONFIG_HOSTDALELEV0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYCONFIG_HOSTDALELEV1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYCONFIG_HOSTDALELEV2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_KEYCONFIG_HOSTDALELEV3 = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_ROM_CTRLA = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_ROM_CTRLA = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_FCR_CTRLA = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_FCR_CTRLA = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_RPMU_VREGCTRL = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_RPMU_VREGCTRL = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_PLL0_CTRL = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_PLL0_CTRL = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_PLL0_FBDIV = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_PLL0_FBDIV = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_PLL0_REFDIV = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_PLL0_REFDIV = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_PLL0_POSTDIVA = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_PLL0_POSTDIVA = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_MCLK_CLKDIV1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_MCLK_CLKDIV1 = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_GCLK_GENCTRL0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_GCLK_GENCTRL0 = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_BROM_BOOTCFGCRC0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_BROM_BOOTCFGCRC1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_BROM_BOOTCFGCRC2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG1_BROM_BOOTCFGCRC3 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_BROM_BOOTCFGCRC0 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_BROM_BOOTCFGCRC1 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_BROM_BOOTCFGCRC2 = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_BROM_BOOTCFGCRC3 = 0xFFFFFFFF;

const uint32_t FUSES_BOOTCFG1_BROM_PAGEEND = 0xFFFFFFFF;
const uint32_t FUSES_BOOTCFG2_BROM_PAGEEND = 0xFFFFFFFF;

// const uint32_t FUSES_DALCFG_DAL;

const uint32_t FUSES_USERCFG1_FSEQ = 0xFFFE0001;
const uint32_t FUSES_USERCFG2_FSEQ = 0xFFFF0000;
const uint32_t FUSES_USERCFG1_AFSEQ = 0xFFFFFFFF;
const uint32_t FUSES_USERCFG2_AFSEQ = 0xFFFFFFFF;

// These are used to configure the watchdog timer. The watchdog is configured to trip at about
// 2048ms and cannot be turned off.
const uint32_t FUSES_USERCFG1_FUCFG0 = FUSES_FUCFG0_WDT_ENABLE_Msk | FUSES_FUCFG0_WDT_ALWAYSON_Msk | FUSES_FUCFG0_WDT_PER(8);
const uint32_t FUSES_USERCFG2_FUCFG0 = FUSES_FUCFG0_WDT_ENABLE_Msk | FUSES_FUCFG0_WDT_ALWAYSON_Msk | FUSES_FUCFG0_WDT_PER(8);

const uint32_t FUSES_USERCFG1_FUCFG1 = 0xFFFFFFFF;
const uint32_t FUSES_USERCFG2_FUCFG1 = 0xFFFFFFFF;

const uint32_t FUSES_USERCFG1_FUCFG2 = 0x79;
const uint32_t FUSES_USERCFG2_FUCFG2 = 0x79;

const uint32_t FUSES_USERCFG1_FUCFG3 = 0x0449;
const uint32_t FUSES_USERCFG2_FUCFG3 = 0x0449;

const uint32_t FUSES_USERCFG1_FUCFG5 = 0xFFFFFFFF;
const uint32_t FUSES_USERCFG2_FUCFG5 = 0xFFFFFFFF;

const uint32_t FUSES_USERCFG1_FUCFG6 = 0x70;
const uint32_t FUSES_USERCFG2_FUCFG6 = 0x70;

const uint32_t FUSES_USERCFG1_FUCFG7 = 0x02;
const uint32_t FUSES_USERCFG2_FUCFG7 = 0x02;

const uint32_t FUSES_USERCFG1_FUCFG8 = 0;
const uint32_t FUSES_USERCFG2_FUCFG8 = 0;

const uint32_t FUSES_USERCFG1_FUCFG9 = 0xFFFFFFFF;
const uint32_t FUSES_USERCFG2_FUCFG9 = 0xFFFFFFFF;

const uint32_t FUSES_USERCFG1_FUCFG16 = 0xFFFFFFFF;
const uint32_t FUSES_USERCFG2_FUCFG16 = 0xFFFFFFFF;

const uint32_t FUSES_USERCFG1_FUCFG24 = 0xFFFFFFFF;
const uint32_t FUSES_USERCFG2_FUCFG24 = 0xFFFFFFFF;



static void DelaySysTicks(uint32_t ticks)
{
    // The SysTick timer is a 24-bit countdown timer, so we set our ticks value, enable the timer,
    // and just wait for it to finish. Testing with an oscilloscope shows that the SysTick timer
    // runs at the same rate as the CPU.
    SysTick->LOAD = ticks;
    SysTick->VAL = 0;               // Write to this to clear CTRL.COUNTFLAG
    SysTick->CTRL = (SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk);

    while(0 == (SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk))
    {}

    SysTick->CTRL = 0;              // Done with the timer, so turn it off.
}

static void DelayMs(uint32_t ms)
{
    // The PIC32CZ CPU starts at 48MHz, so that's 48000 SysTick ticks per ms.
    while(ms > 10)
    {
        DelaySysTicks(10 * 48000);
        ms -= 10;
    }

    if(ms)
        DelaySysTicks(ms * 48000);
}


int main()
{
    /*  This board has LEDs on PB21 and PB22. This will use PB21.
        */
    uint32_t led_group = 1;         // group 0 is Port A, group 1 is Port B, etc.
    uint32_t led_pin = 21;

    // There is one PINCFG register per port pin.
    // This disables slew rate control, open-drain, pull-ups or -downs (depends on the OUT bit), the
    // input buffer, and the peripheral mux (so the PORT controls the pin).
    PORT_REGS->GROUP[led_group].PORT_PINCFG[led_pin] = 0;
    // This sets the pin as an output.
    PORT_REGS->GROUP[led_group].PORT_DIRSET = (1 << led_pin);
    // This sets the output as low. If the pin were an input, this would select the pull-down.
    PORT_REGS->GROUP[led_group].PORT_OUTCLR = (1 << led_pin);

    DelayMs(500);

    while(true)
    {
        PORT_REGS->GROUP[led_group].PORT_OUTTGL = (1 << led_pin);
        DelayMs(2000);      // The watchdog should trip while in this delay.
    }

    return 0;
}