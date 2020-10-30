#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <EasyButton.h>

#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels
#define BUTTON_PIN 0

// ===============================================
// Global Vars
// ===============================================
int shutter = 0; // 0 is closed, 1 is open
String reply;
EasyButton button(BUTTON_PIN);

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
// ===============================================


// ===============================================
//          Functions
// ===============================================
void onPressed() {
    
    int value = digitalRead(LED_BUILTIN);
    digitalWrite(LED_BUILTIN, !value);
    if (value == HIGH)
        shutter = 1;
    else
        shutter = 0;
}
// ===============================================


void setup()
{
    button.begin();
    button.onPressed(onPressed);

    Serial.begin(115200);
    
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN,HIGH);

    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C))
    { // Address 0x3D for 128x64
        Serial.println(F("SSD1306 allocation failed"));
        for (;;)
            ;
    }
    display.clearDisplay();
    display.setTextSize(3);
    display.setTextColor(WHITE);
    display.display();
}

void loop()
{
    button.read();
    if (shutter == 1)
    {
        display.clearDisplay();
        display.setCursor(0, 10);
        display.println("OPEN");
        display.display();
    }
    else
    {
        display.clearDisplay();
        display.setCursor(0, 10);
        display.println("CLOSED");
        display.display();
    }

    if (Serial.available() > 0) {
        String msg = Serial.readString();
        msg.trim();

        if( msg == "close-shutter"){
            Serial.println("Closing shutter .........");
            shutter = 0;
            digitalWrite(LED_BUILTIN, HIGH);
        } 
        else if( msg == "open-shutter"){
            Serial.println("Opeing shutter .........");
            shutter = 1;
            digitalWrite(LED_BUILTIN, LOW);
        }
        else if(msg == "status"){
            reply = (shutter == 1) ? "open" : "closed";
            Serial.println(reply);
        }

    }
    Serial.println((shutter == 1) ? "open" : "closed");
}