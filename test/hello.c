/* hello.c

   Okay, we can blink an LED so now let's try a REAL "Hello, world!" app. This test will try to
   set up enough stuff to get LLVM-libc's printf() and friends to work. This is useful because it
   indicates what a baremetal app would implement to have console-like functionality.
   
   The functions implemented will be application-specific. Maybe you want to print to a serial port,
   an internal log, or over UDP. This app will try to bit-bang a simple serial output for giggles.
   File IO requires even more setup and for now is probably limited to using the standard file IO
   handles (stdout, stdin, stderr).

   This test won't set up the device configuration registers. Previous testing suggests that
   Microchip tools program on useful defaults if no config regs are specific. A different file will
   test setting those up.

   This is running on a PIC32CZ CA80 Curiosity Ultra board, which has a PIC32CZ8110CA80208 device
   on it. If you want to build this on a different device, substitute the name of your device in
   the below command where you see the device name.

   Build this file with 'path/to/clang --config pic32cz8110ca80208.cfg -o hello.elf hello.c'
   Make it an Intel Hex file with 'path/to/llvm-objcopy -O ihex hello.elf hello.hex'
   */

#include <which_pic32.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>

#ifndef __PIC32C
#  warning This was tested on a PIC32C device only.
#endif

static void write_serial_byte(char c);

/*******
 * START OF LLVM LIBC STUFF
 *******/

/* LLVM-libc wants us to define a "cookie" structure for the standard streams. Presumably the intent
   is to have it hold app-specific members for you. For example, if you were sending stdout over
   UDP, then you would presumably have the cookie struct contain connection info--like IP address,
   port, and a socket handle--to make that happen.

   I don't think there's a cookie for file IO stuff, though that would be handy.
   */
struct __llvm_libc_stdio_cookie
{
    // Nothing for now
};

/* These cookies are ways for LLVM-libc to tell you which stream to read from or write to. You would
   check if the stream passed to one of the below functions matches one of these and perform the
   appropriate action if so. Chances are an embedded application will dump both stdout and stderr to
   the same location, such as a serial port, but they don't have to.
   
   These cookie declarations and the below functions would be 'extern "C"' in a cpp file.
   */
struct __llvm_libc_stdio_cookie __llvm_libc_stdin_cookie;
struct __llvm_libc_stdio_cookie __llvm_libc_stdout_cookie;
struct __llvm_libc_stdio_cookie __llvm_libc_stderr_cookie;


// We are not reading anything in this test, but presumably you would check if the passed-in cookie
// pointer points to your __llvm_libc_stdin_cookie above. If so, read some data from whatever input
// you have, like a serial port, and put that into 'buf'. The size of the buffer is 'size'. This
// returns the number of bytes actually read or -1 if an error ocurred.
//
// This function is meant to be usable as the 'read' function passed to the POSIX fopencookie()
// function.
ssize_t __llvm_libc_stdio_read(void *cookie, char *buf, size_t size)
{
    ssize_t bytes_read = 0;

    // if(&__llvm_libc_stdin_cookie == cookie)
    // {
    //     Read stuff from serial port or whatever here and put that info 'buf'.
    //     bytes_read = number of bytes read into 'buf'
    // }

    return bytes_read;
}

// Check if the passed-in cookie pointer points to either your __llvm_libc_stdout_cookie or
// __llvm_libc_stderr_cookie. If so, then send the data from 'buf' to your output, like a serial
// port. Return the number of bytes you were able to write to your output. Never return a negative
// value.
//
// This function is meant to be usable as the 'write' function passed to the POSIX fopencookie()
// function.
ssize_t __llvm_libc_stdio_write(void *cookie, const char *buf, size_t size)
{
    ssize_t bytes_written = 0;

    // These could go to different places, but here we'll just send them to the same place.
    if(&__llvm_libc_stdout_cookie == cookie  ||  &__llvm_libc_stderr_cookie == cookie)
    {
        for(int i = 0; i < size; ++i)
        {
            write_serial_byte(buf[i]);
        }

        bytes_written = size;
    }

    return bytes_written;
}

/*******
 * END OF LLVM LIBC STUFF
 *******/


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
    // We probably should subtract 1 since usually periodic timers tick once more than their
    // set period, but meh.
    while(ms > 10)
    {
        DelaySysTicks(10 * 48000);
        ms -= 10;
    }

    if(ms)
        DelaySysTicks(ms * 48000);
}

/* This board has LEDs on PB21 and PB22. This will use PB21.
   */
uint32_t led_group = 1;         // group 0 is Port A, group 1 is Port B, etc.
uint32_t led_pin = 21;
uint32_t blink_count = 0;

/* We will use pin PC0 for a bit-banged serial port. On the PIC32CZ CA80 Curiosity Ultra board I'm 
   using, this goes out to pin 11 of header EXT1.
   */
uint32_t serial_group = 2;
uint32_t serial_pin = 0;

int main()
{

    // There is one PINCFG register per port pin.
    // This disables slew rate control, open-drain, pull-ups or -downs (depends on the OUT bit), the
    // input buffer, and the peripheral mux (so the PORT controls the pin).
    PORT_REGS->GROUP[led_group].PORT_PINCFG[led_pin] = 0;
    // This sets the pin as an output.
    PORT_REGS->GROUP[led_group].PORT_DIRSET = (1 << led_pin);
    // This sets the output as low. If the pin were an input, this would select the pull-down.
    PORT_REGS->GROUP[led_group].PORT_OUTCLR = (1 << led_pin);

    PORT_REGS->GROUP[serial_group].PORT_PINCFG[serial_pin] = 0;
    PORT_REGS->GROUP[serial_group].PORT_DIRSET = (1 << serial_pin);
    PORT_REGS->GROUP[serial_group].PORT_OUTSET = (1 << serial_pin);     // serial idles high

#warning TOOD: Do I need to turn off buffering for the IO?
    // LLVM-libc might already not buffer since it presumably would just call your stdio functions
    // above. It'd be up to you to buffer.

    while(true)
    {
        DelayMs(1000);
        PORT_REGS->GROUP[led_group].PORT_OUTTGL = (1 << led_pin);

        ++blink_count;
        printf("Hello! Times blinked: %u\n", blink_count);
    }

    return 0;
}



/* We're going to bit-bang a serial port because I don't feel like trying to figure out how the
   SERCOM peripheral on the PIC32CZ works right now. I mean, the datasheet is probably wrong, anyway,
   if my past experience holds true.

   This will output using port pin PC0. On the PIC32CZ CA80 Curiosity Ultra board I'm using, this
   goes out to pin 11 of header EXT1.
   */
static void write_serial_byte(char c)
{
// 19200 baud
#define kSerialDelay  (48000000 / 19200)

    // Start bit: go from idle (high) to active (low)
    PORT_REGS->GROUP[serial_group].PORT_OUTCLR = (1 << serial_pin);
    DelaySysTicks(kSerialDelay);

    // Data bits
    for(int i = 0; i < 8; ++i)
    {
        if(c & 0x01)
            PORT_REGS->GROUP[serial_group].PORT_OUTSET = (1 << serial_pin);
        else
            PORT_REGS->GROUP[serial_group].PORT_OUTCLR = (1 << serial_pin);

        DelaySysTicks(kSerialDelay);
        c >>= 1;
    }

    // Stop bit: go back to idle (high)
    PORT_REGS->GROUP[serial_group].PORT_OUTSET = (1 << serial_pin);
    DelaySysTicks(kSerialDelay);
}
