/*
 *
 * Copyright (C)2015-2017 Laurentiu Badea
 *
 * This file may be redistributed under the terms of the MIT license.
 * A copy of this license has been included with this distribution in the file LICENSE.
 */
#include <Arduino.h>
#include "BasicStepperDriver.h"
#include "MultiDriver.h"
#include "SyncDriver.h"

//#define MOTOR_STEPS_PAN 600
#define MOTOR_STEPS_TILT 200
#define RPM 60         //180 seems to be max
#define MOTOR_ACCEL 600 //Quite fast accel (600)
#define MOTOR_DECEL 900 //Very fast decel (900)
#define MICROSTEPS 64 // Hardware microstepping by driver
#define REV_STEPS_PAN 38400
#define REV_STEPS_TILT MICROSTEPS*MOTOR_STEPS_TILT

#define PAN_DIR 4
#define PAN_STEP 5
#define PAN_ENABLE 6

#define TILT_DIR 8
#define TILT_STEP 9
#define TILT_ENABLE 10

#define SERIAL_BUFF 4
unsigned char command[SERIAL_BUFF];
BasicStepperDriver motorPAN(600, PAN_DIR, PAN_STEP, PAN_ENABLE);
BasicStepperDriver motorTILT(MOTOR_STEPS_TILT, TILT_DIR, TILT_STEP, TILT_ENABLE);
SyncDriver controller(motorPAN, motorTILT);

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
    
    //Serial.println("Stepper Setup Complete");
    //Serial.print("Revolution steps:   ");
    //Serial.println(REV_STEPS);
    Serial.println("READY");
}

void loop() {
    //Grab int from serial for new target
    
    if (Serial.available() >= SERIAL_BUFF)
    {
      Serial.readBytes(command,SERIAL_BUFF);
      PanTargetINT = (command[0]<<8) + command[1];
      PanTargetAngle = PanTargetINT*0.015;
      //Serial.write(PanTargetINT);
      PanTargetAngle = fmod(PanTargetAngle,360);
      PanTargetSteps = (int)(PanTargetAngle*600*MICROSTEPS/360);
//      Serial.print("New target:     ");
//      Serial.println(PanTargetAngle);
//      Serial.print("Step target:    ");
//      Serial.println(PanTargetSteps);
      
      
      //Don't have to worry about timing because all this is done before nextAction()
      PanCurrentSteps += motorPAN.getDirection()*motorPAN.getStepsCompleted();
      PanCurrentSteps %= 38400;
//      Serial.print("Current Steps:  ");
//      Serial.println(PanCurrentSteps);
//      Serial.print("Direction:      ");
//      Serial.println(motorPAN.getDirection());

      
      //Find which direction is shortest
      long stepDiffPan = PanTargetSteps-PanCurrentSteps; 
      if (stepDiffPan > 38400/2 )
        stepDiffPan -= 38400;
      else if (stepDiffPan < -1*38400/2)
        stepDiffPan += 38400;
        
//      Serial.print("Diff:           ");
//      Serial.println(stepDiff);
//      Serial.println("~~~~~~~~~~~~~~~");
      //setup new move
      //motorPAN.startMove(stepDiff,0);

      //  TILT TILT TILT   //
      TiltTargetINT = (command[2]<<8) + command[3];
      TiltTargetAngle = TiltTargetINT*0.015; //pwm so just need angle
      //Serial.write(TiltTargetINT);
      TiltTargetAngle = fmod(TiltTargetAngle,360);
      TiltTargetSteps = (int)(TiltTargetAngle*MOTOR_STEPS_TILT*MICROSTEPS/360);
      TiltCurrentSteps += motorTILT.getDirection()*motorTILT.getStepsCompleted();
      TiltCurrentSteps %= REV_STEPS_TILT;
      long stepDiff = TiltTargetSteps-TiltCurrentSteps; 
      if (stepDiff > REV_STEPS_TILT/2 )
        stepDiff -= REV_STEPS_TILT;
      else if (stepDiff < -1*REV_STEPS_TILT/2)
        stepDiff += REV_STEPS_TILT;  
      //motorTILT.startMove(stepDiff,0);
      controller.startMove(stepDiffPan, stepDiff);
    }
    
    long wait_time_micros = controller.nextAction();
}
