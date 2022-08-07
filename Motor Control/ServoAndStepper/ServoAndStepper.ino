/*
 * Using accelerated motion ("linear speed") in nonblocking mode
 *
 * Copyright (C)2015-2017 Laurentiu Badea
 *
 * This file may be redistributed under the terms of the MIT license.
 * A copy of this license has been included with this distribution in the file LICENSE.
 */
#include <Arduino.h>
#include "BasicStepperDriver.h"
#include <Servo.h>

#define MOTOR_STEPS 200
#define RPM 40         //180 seems to be max
#define MOTOR_ACCEL 600 //Quite fast accel
#define MOTOR_DECEL 900 //Very fast decel
#define MICROSTEPS 16 // Hardware microstepping by driver
#define REV_STEPS MICROSTEPS*MOTOR_STEPS

#define SERVO 10
#define DIR 8
#define STEP 11
#define SLEEP 13 // optional (just delete SLEEP from everywhere if not used)
#define ENABLE 4

#define SERIAL_BUFF 4
unsigned char command[SERIAL_BUFF];
BasicStepperDriver motorPAN(MOTOR_STEPS, DIR, STEP, ENABLE);
Servo myservo;

float PanTargetAngle = 0;
uint16_t PanTargetINT = 0;
long PanCurrentSteps = 0;
long PanTargetSteps = 0; 

float TiltTargetAngle = 0;
uint16_t TiltTargetINT = 0;

void setup() {
    Serial.begin(74880);

    motorPAN.begin(RPM, MICROSTEPS);
    motorPAN.setSpeedProfile(motorPAN.LINEAR_SPEED, MOTOR_ACCEL, MOTOR_DECEL);
    motorPAN.enable();

    myservo.attach(SERVO);
    Serial.println("Stepper Setup Complete");
    Serial.print("Revolution steps:   ");
    Serial.println(REV_STEPS);
    Serial.println("READY");
}

void loop() {
    //Grab int from serial for new target
    
    if (Serial.available() >= SERIAL_BUFF)
    {
      Serial.readBytes(command,SERIAL_BUFF);
      PanTargetINT = (command[0]<<8) + command[1];
      PanTargetAngle = PanTargetINT*0.015;
      Serial.write(PanTargetINT);
      PanTargetAngle = fmod(PanTargetAngle,360);
      PanTargetSteps = (int)(PanTargetAngle*MOTOR_STEPS*MICROSTEPS/360);
//      Serial.print("New target:     ");
//      Serial.println(PanTargetAngle);
//      Serial.print("Step target:    ");
//      Serial.println(PanTargetSteps);
      
      
      //Don't have to worry about timing because all this is done before nextAction()
      PanCurrentSteps += motorPAN.getDirection()*motorPAN.getStepsCompleted();
      PanCurrentSteps %= REV_STEPS;
//      Serial.print("Current Steps:  ");
//      Serial.println(PanCurrentSteps);
//      Serial.print("Direction:      ");
//      Serial.println(motorPAN.getDirection());

      
      //Find which direction is shortest
      long stepDiff = PanTargetSteps-PanCurrentSteps; 
      if (stepDiff > REV_STEPS/2 )
        stepDiff -= REV_STEPS;
      else if (stepDiff < -1*REV_STEPS/2)
        stepDiff += REV_STEPS;
        
//      Serial.print("Diff:           ");
//      Serial.println(stepDiff);
//      Serial.println("~~~~~~~~~~~~~~~");
      //setup new move
      motorPAN.startMove(stepDiff,0);

      //  TILT TILT TILT   //
      TiltTargetINT = (command[2]<<8) + command[3];
      TiltTargetAngle = map(int(TiltTargetINT*0.015),0,360,0,255); //pwm so just need angle
      myservo.write(TiltTargetAngle);
  
    }
    
    long wait_time_micros = motorPAN.nextAction();
    
}
