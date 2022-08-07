/*
 *
 * Copyright (C)2015-2017 Laurentiu Badea
 *
 * This file may be redistributed under the terms of the MIT license.
 * A copy of this license has been included with this distribution in the file LICENSE.
 */
#include <Arduino.h>
#include "BasicStepperDriver.h"

#define MOTOR_STEPS 200
#define RPM 60         //180 seems to be max
#define MOTOR_ACCEL 200 //Quite fast accel (600)
#define MOTOR_DECEL 500 //Very fast decel (900)
#define MICROSTEPS 64 // Hardware microstepping by driver
#define REV_STEPS MICROSTEPS*MOTOR_STEPS

#define PAN_SERVO 10
#define PAN_DIR 8
#define PAN_STEP 11
#define PAN_ENABLE 4

#define TILT_SERVO 10
#define TILT_DIR 8
#define TILT_STEP 11
#define TILT_ENABLE 4

#define SERIAL_BUFF 4
unsigned char command[SERIAL_BUFF];
BasicStepperDriver motorPAN(MOTOR_STEPS, PAN_DIR, PAN_STEP, PAN_ENABLE);
BasicStepperDriver motorTILT(MOTOR_STEPS, TILT_DIR, TILT_STEP, TILT_ENABLE);

float PanTargetAngle = 0;
uint16_t PanTargetINT = 0;
long PanCurrentSteps = 0;
long PanTargetSteps = 0; 

float TiltTargetAngle = 0;
uint16_t TiltTargetINT = 0;
long TiltCurrentSteps = 0;
long TiltTargetSteps = 0; 

void setup() {
    Serial.begin(74880);

    motorPAN.begin(RPM, MICROSTEPS);
    motorPAN.setSpeedProfile(motorPAN.LINEAR_SPEED, MOTOR_ACCEL, MOTOR_DECEL);
    motorPAN.enable();

    motorTILT.begin(RPM, MICROSTEPS);
    motorTILT.setSpeedProfile(motorTILT.LINEAR_SPEED, MOTOR_ACCEL, MOTOR_DECEL);
    motorTILT.enable();
    
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
      Serial.write(TiltTargetINT);
      TiltTargetAngle = fmod(TiltTargetAngle,360);
      TiltTargetSteps = (int)(TiltTargetAngle*MOTOR_STEPS*MICROSTEPS/360);
      TiltCurrentSteps += motorTILT.getDirection()*motorTILT.getStepsCompleted();
      TiltCurrentSteps %= REV_STEPS;
      stepDiff = TiltTargetSteps-TiltCurrentSteps; 
      if (stepDiff > REV_STEPS/2 )
        stepDiff -= REV_STEPS;
      else if (stepDiff < -1*REV_STEPS/2)
        stepDiff += REV_STEPS;  
      motorTILT.startMove(stepDiff,0);
    }
    
    long wait_time_micros = motorPAN.nextAction();
    
}
