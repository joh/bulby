#include <Arduino.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>

#include "hsv.h"

#define RED_PIN 10
#define GREEN_PIN 6
#define BLUE_PIN 9
#define TONE_PIN 8

#define BUF_SIZE 128
#define PROMPT "> "

char buf[BUF_SIZE];
unsigned int buf_pos;
int red, green, blue;

void hue_cycle();

/*
 * Serial.printf()
 */
int print(const char *format, ...)
{
    char tmp[128]; // resulting string limited to 128 chars
    va_list args;

    va_start (args, format );
    vsnprintf(tmp, 128, format, args);
    va_end (args);

    return Serial.print(tmp);
}

int println(const char *format, ...)
{
    char tmp[128]; // resulting string limited to 128 chars
    va_list args;

    va_start (args, format );
    vsnprintf(tmp, 128, format, args);
    va_end (args);

    return Serial.println(tmp);
}

void set_color(int r, int g, int b)
{
    r = constrain(r, 0, 255);
    g = constrain(g, 0, 255);
    b = constrain(b, 0, 255);

    analogWrite(RED_PIN, r);
    analogWrite(GREEN_PIN, g);
    analogWrite(BLUE_PIN, b);
}

void set_tone(unsigned int freq)
{
    if (0 == freq)
        noTone(TONE_PIN);
    else
        tone(TONE_PIN, freq);
}

void set_color_hsv(int h, int s, int v) {
    int r, g, b;

    HSVtoRGB(&r, &g, &b, h, s, v);

    set_color(r, g, b);
}

void random_color(int *r, int *g, int *b) {
    int i = 0, j = 0, k = 0;

    while (i + j + k == 0) {
        i = random(0, 2);
        j = random(0, 2);
        k = random(0, 2);
    }

    *r = i * 255;
    *g = j * 255;
    *b = k * 255;
}

void fade_in(int r, int g, int b) {
    int i;

    for (i = 0; i <= 255; i++) {
        set_color(r * i / 255, g * i / 255, b * i / 255);
        delay(20);
    }
}

void fade_out(int r, int g, int b) {
    int i;

    for (i = 255; i >= 0; i--) {
        set_color(r * i / 255, g * i / 255, b * i / 255);
        delay(20);
    }
}

void hue_cycle() {
    int h, r, g, b;

//    HSVtoRGB(&r, &g, &b, 0, 255, 255);

//    fade_in(r, g, b);

    for (h = 0; h < 360; h++) {
        set_color_hsv(h, 255, 255);
        delay(10);
    }

//    HSVtoRGB(&r, &g, &b, 359, 255, 255);

//    fade_out(r, g, b);
}

/*
 * Parse input line
 */
void parse(char *line)
{
    char *command;
    char *arg;
    const char *delim = " \n\r";

    int i, n;
    int r, g, b, freq;

    command = strtok(line, delim);

    if (NULL == command) return;

    if (0 == strcmp(command, "color")) {
        arg = strtok(NULL, delim);
        if (NULL == arg) goto err_args_missing;
        red = atoi(arg);

        arg = strtok(NULL, delim);
        if (NULL == arg) goto err_args_missing;
        green = atoi(arg);

        arg = strtok(NULL, delim);
        if (NULL == arg) goto err_args_missing;
        blue = atoi(arg);

        set_color(red, green, blue);
        return;
    }

    if (0 == strcmp(command, "tone")) {
        arg = strtok(NULL, delim);
        if (NULL == arg) goto err_args_missing;
        freq = atoi(arg);

        set_tone(freq);
        return;
    }

    if (0 == strcmp(command, "help")) {
        println("Available commands:");
        println("  color <r> <g> <b>");
        println("  tone <freq>");
        println("  help");
        return;
    }

    println("Unrecognized command: '%s'", command);
    goto err_help;

err_args_missing:
    println("%s: not enough arguments", command);

err_help:
    println("Try 'help'");

}

void setup() {
    pinMode(RED_PIN, OUTPUT);
    pinMode(GREEN_PIN, OUTPUT);
    pinMode(BLUE_PIN, OUTPUT);
    pinMode(TONE_PIN, OUTPUT);

    randomSeed(analogRead(0));

    /*hue_cycle();*/

    Serial.begin(57600);
}

void loop() {
    char c;

    if (Serial.available() > 0) {
        c = (char)Serial.read();

        //println("0x%04x", c);
        //return;

        if (c == '\r') {
            buf[buf_pos] = '\0';
            Serial.println();
            parse(buf);

            buf[0] = '\0';
            buf_pos = 0;

            Serial.print(PROMPT);
        } else if (c >= 0x20 && c < 0x7f) {
            /* Visible character */
            buf[buf_pos] = c;
            buf_pos = (buf_pos + 1) % BUF_SIZE;
            Serial.print(c);
        } else if (c == 0x03 || c == 0x04) {
            /* Ctrl-C or Ctrl-D */
            buf[0] = '\0';
            buf_pos = 0;

            Serial.println();
            Serial.print(PROMPT);
        } else if (c == 0x7f && buf_pos > 0) {
            /* Backspace */
            buf[buf_pos] = '\0';
            buf_pos--;

            Serial.write(0x1b); // Move back 1 char
            Serial.write("[D");
            Serial.write(" ");  // print space
            Serial.write(0x1b); // Move back 1 char
            Serial.write("[D");
        } else {
            /* Unknown character */
            //Serial.println(c, HEX);
        }
    }
}

