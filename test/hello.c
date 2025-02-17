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

static void add_serial_byte(char c);
static void send_pending_serial_data(void);

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
   the same location, such as a serial port, but they don't have to. From what I can tell, libc
   uses stderr for printf(), puts(), and so on.
   
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
            add_serial_byte(buf[i]);
        }

        bytes_written = size;
    }

    return bytes_written;
}

/*******
 * END OF LLVM LIBC STUFF
 *******/


/* This board has LEDs on PB21 and PB22. This will use PB21. If the LED works, then we know that
   these static variables are getting initialized correctly from the .data initialization code
   in the startup module.
   */
static uint32_t led_group = 1;         // group 0 is Port A, group 1 is Port B, etc.
static uint32_t led_pin = 21;
static uint32_t blink_count = 0;

/* We will use pin PC0 for a bit-banged serial port. On the PIC32CZ CA80 Curiosity Ultra board I'm 
   using, this goes out to pin 11 of header EXT1.
   */
static uint32_t serial_group = 2;
static uint32_t serial_pin = 0;


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

    while(true)
    {
        double print_time;

        DelayMs(1000);
        ++blink_count;
        PORT_REGS->GROUP[led_group].PORT_OUTTGL = (1 << led_pin);

        // Use the 24-bit countdown timer to time our print. At 48MHz, we have just under 350ms.
        SysTick->LOAD = 0xFFFFFF;
        SysTick->VAL = 0;
        SysTick->CTRL = (SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk);
        printf("Hello! Times blinked: %u\n", blink_count);
        print_time = (double)(0xFFFFFF - SysTick->VAL);
        SysTick->CTRL = 0;

        SysTick->LOAD = 0xFFFFFF;
        SysTick->VAL = 0;
        SysTick->CTRL = (SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk);
        printf("->that last print took %fms\n", (print_time / 48000.0));
        print_time = (double)(0xFFFFFF - SysTick->VAL);
        SysTick->CTRL = 0;

        printf("---> and THAT last print took %fms\n", (print_time / 48000.0));

        send_pending_serial_data();

        // NOTE:
        // Here are some performance numbers. We leave the CPU running at its default 48MHz and the
        // libraries should be built with O2 optimizations. There are a couple of CMake options we
        // can tweak in ../cmake_caches/pic32clang-target-runtimes.cmake. In particular, we need to
        // use the USE_DYADIC_FLOAT option because otherwise printf() uses tables that take an extra
        // 100kB of space!
        //
        // With no optimizations and USE_FLOAT320 CMake option on, flash usage is about 47.4kB.
        // Those two print times are about 0.1ms and 0.35ms, respectively. With USE_FLOAT32 off, 
        // flash usage rises to about 58.8kb. The times are about 0.1ms and 0.18ms, respectively.
        // That is much faster for doubles at the expense of extra flash usage.
        // 
        // With O1 optimization and USE_FLOAT320 off, flash usage changes little to about 58.3kB.
        // The times drop to 0.087ms and 0.167ms.
        //
        // With no optimizations, USE_FLOAT320 off, and LIBC_COPT_FLOAT_TO_STR_NO_TABLE defined,
        // flash usage is about 56.4kB. The times are about 0.1ms and 0.186ms. With USE_FLOAT32 on,
        // flash usage is about 47.4kB. The times are about 0.1ms and 0.37ms. In other words, that
        // define saves a couple of kB in the USE_FLOAT320 off case with little other impact.
    }

    return 0;
}



/* We're going to bit-bang a serial port because I don't feel like trying to figure out how the
   SERCOM peripheral on the PIC32CZ works right now. I mean, the datasheet is probably wrong anyway,
   if my past experience holds true.

   This will output using port pin PC0. On the PIC32CZ CA80 Curiosity Ultra board I'm using, this
   goes out to pin 11 of header EXT1.
   */
static char serial_buf[512];
static int serial_count = 0;

static void add_serial_byte(char c)
{
    serial_buf[serial_count] = c;
    ++serial_count;
}

static void send_pending_serial_data()
{
// 19200 baud
#define kSerialDelay  (48000000 / 19200)

    char *bufptr = serial_buf;

    while(serial_count > 0)
    {
        char c = *bufptr;
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

        --serial_count;
        ++bufptr;
    }
}