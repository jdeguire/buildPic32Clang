/* interrupt.c

   This is the "Hello, world!" of the embedded world: blinking a single LED! This is a simple yet
   very useful test. It can tell us if the CPU is running at roughly the speed we expect it, if we
   can access device registers, and if the startup code is setting up our stack to something at
   least somewhat reasonable.

   This is a little different from the normal blinky test: here we will use an interrupt to run
   a free-running timer. We will blink the LED from that. If the interrupt is working, then we will
   see the LED blink like in the normal blinky test.

   This test won't set up the device configuration registers. Previous testing suggests that
   Microchip tools program on useful defaults if no config regs are specific. A different file will
   test setting those up.

   This is running on a PIC32CZ CA80 Curiosity Ultra board, which has a PIC32CZ8110CA80208 device
   on it. If you want to build this on a different device, substitute the name of your device in
   the below command where you see the device name.

   Build this file with 'path/to/clang --config pic32cz8110ca80208.cfg -o interrupt.elf interrupt.c'
   Make it an Intel Hex file with 'path/to/llvm-objcopy -O ihex interrupt.elf interrupt.hex'
   */

#include <which_pic32.h>
#include <stdint.h>
#include <stdbool.h>

#ifndef __PIC32C
#  warning This was tested on a PIC32C device only.
#endif

volatile uint32_t g_1ms_tick_timer = 0;

/*  This board has LEDs on PB21 and PB22. This will use PB21.
    */
uint32_t led_group = 1;         // group 0 is Port A, group 1 is Port B, etc.
uint32_t led_pin = 21;
uint32_t led2_pin = 22;
   

/* Configure this timer to run and fire an interrupt every 1ms to give us a free-running tick timer.
 */
static void SetupSysTickTimer(void)
{
    // ARM chips use higher numbers to mean LOWER priority. On the PIC32C chips, 7 is the lowest
    // priority and 0 is the highest we can use. Reset, NMI, and HardFaults have negative priority
    // and so win out over anything we could do. The default priority for interrupts is 0.
    NVIC_SetPriority(SysTick_IRQn, 6);
    NVIC_ClearPendingIRQ(SysTick_IRQn);
    NVIC_EnableIRQ(SysTick_IRQn);

    // The SysTick timer is a 24-bit countdown timer, so we set our ticks value, enable the timer,
    // and let it wrap around. Testing with an oscilloscope shows that the SysTick timer
    // runs at the same rate as the CPU. Timers usually tick one extra beyond the period value, so
    // we subtract 1 to handle that. The CPU runs at 48MHz when it first starts up.
    SysTick->LOAD = 48000 - 1;
    SysTick->VAL = 0;               // Write to this to clear CTRL.COUNTFLAG
    SysTick->CTRL = (SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk);
}

/* This is our interrupt handler for SysTick. The compiler is set up similarly to how we used to do
   it on the PIC24H parts in that you use a special name for the function instead of specifying the
   vector in an attribute. Notice how this looks like a regular C function. This is by design for
   the Cortex-M. In short, the CPU puts a special value in the return address register to act as a
   "return from interrupt" instead of needing a special instruction. It also handles stacking and
   unstacking certain registers for us.
   */
void SysTick_Handler(void)
{
    // I'm not sure if we need to clear CTRL.COUNTFLAG, but no harm in doing it. A read clears it.
    SysTick->CTRL;
    ++g_1ms_tick_timer;

    if(0 == (g_1ms_tick_timer & 0xFF))
    {
        PORT_REGS->GROUP[led_group].PORT_OUTTGL = (1 << led2_pin);
    }

    // We do not have to manually clear the interrupt flag from the interrupt controller on
    // Cortex-M CPUs. We generally need to clear only flags that are part of a peripheral.
}

int main()
{
    uint32_t led_timer = 0;

    // There is one PINCFG register per port pin.
    // This disables slew rate control, open-drain, pull-ups or -downs (depends on the OUT bit), the
    // input buffer, and the peripheral mux (so the PORT controls the pin).
    PORT_REGS->GROUP[led_group].PORT_PINCFG[led_pin] = 0;
    // This sets the pin as an output.
    PORT_REGS->GROUP[led_group].PORT_DIRSET = (1 << led_pin);
    // This sets the output as low. If the pin were an input, this would select the pull-down.
    PORT_REGS->GROUP[led_group].PORT_OUTCLR = (1 << led_pin);

    PORT_REGS->GROUP[led_group].PORT_PINCFG[led2_pin] = 0;
    PORT_REGS->GROUP[led_group].PORT_DIRSET = (1 << led2_pin);
    PORT_REGS->GROUP[led_group].PORT_OUTSET = (1 << led2_pin);

    SetupSysTickTimer();

    while(true)
    {
        if((g_1ms_tick_timer - led_timer) > 2000)
        {
            PORT_REGS->GROUP[led_group].PORT_OUTTGL = (1 << led_pin);
            led_timer = g_1ms_tick_timer;
        }
    }

    return 0;
}