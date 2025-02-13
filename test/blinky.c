/* blinky.c

   This is the "Hello, world!" of the embedded world: blinking a single LED! This is a simple yet
   very useful test. It can tell us if the CPU is running at roughly the speed we expect it, if we
   can access device registers, and if the startup code is setting up our stack to something at
   least somewhat reasonable.

   This test won't set up the device configuration registers. Previous testing suggests that
   Microchip tools program on useful defaults if no config regs are specific. A different file will
   test setting those up.

   This is running on a PIC32CZ CA80 Curiosity Ultra board, which has a PIC32CZ8110CA80208 device
   on it. If you want to build this on a different device, substitute the name of your device in
   the below command where you see the device name.

   Build this file with 'path/to/clang --config pic32cz8110ca80208.cfg -o blinky.elf blinky.c'
   Make it an Intel Hex file with 'path/to/llvm-objcopy -O ihex blinky.elf blinky.hex'
   */

#include <which_pic32.h>
#include <stdint.h>
#include <stdbool.h>

#ifndef __PIC32C
#  warning This was tested on a PIC32C device only.
#endif

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

    while(true)
    {
        DelayMs(1000);
        PORT_REGS->GROUP[led_group].PORT_OUTTGL = (1 << led_pin);
    }

    return 0;
}