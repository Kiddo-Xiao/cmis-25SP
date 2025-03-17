import java.util.ArrayList;
import java.util.Collections;
import java.net.DatagramSocket;
import java.net.DatagramPacket;
import java.net.SocketException;
import java.io.IOException;

int index = 0;
float border = 0;
int trialCount = 5;

int trialIndex = 0;
int errorCount = 0;
float errorPenalty = 1.0f;
int startTime = 0;
int finishTime = 0;
boolean userDone = false;

final int screenPPI = 72;

float logoX = 500;
float logoY = 500;
float logoZ = 50f;
float logoRotation = 0;

private class Destination {
  float x = 0;
  float y = 0;
  float rotation = 0;
  float z = 0;
}

ArrayList<Destination> destinations = new ArrayList<Destination>();

void setup() {
  size(1000, 800);  
  rectMode(CENTER);
  textFont(createFont("Arial", inchToPix(.3f)));
  textAlign(CENTER);
  rectMode(CENTER);

  border = inchToPix(2f);

  println("creating " + trialCount + " targets");
  for (int i = 0; i < trialCount; i++) {
    Destination d = new Destination();
    d.x = random(border, width - border);
    d.y = random(border, height - border);
    d.rotation = random(0, 360);
    int j = (int)random(20);
    d.z = ((j % 5) + 1) * inchToPix(.5f);
    destinations.add(d);
    println("created target with " + d.x + "," + d.y + "," + d.rotation + "," + d.z);
  }

  Collections.shuffle(destinations);

  new UDPReceiver(5005, true).start();  // for position
  new UDPReceiver(5006, false).start(); // for rotation and size
}

void draw() {
  background(40);
  fill(200);
  noStroke();

  if (userDone) {
    text("User completed " + trialCount + " trials", width / 2, inchToPix(.4f));
    text("User had " + errorCount + " error(s)", width / 2, inchToPix(.4f) * 2);
    text("User took " + (finishTime - startTime) / 1000f / trialCount + " sec per destination", width / 2, inchToPix(.4f) * 3);
    text("User took " + ((finishTime - startTime) / 1000f / trialCount + (errorCount * errorPenalty)) + " sec per destination inc. penalty", width / 2, inchToPix(.4f) * 4);
    return;
  }

  for (int i = trialIndex; i < trialCount; i++) {
    pushMatrix();
    Destination d = destinations.get(i);
    translate(d.x, d.y);
    rotate(radians(d.rotation));
    noFill();
    strokeWeight(3f);
    
    if (trialIndex == i) {
      if (checkForSuccess()) {
        stroke(0, 255, 0, 192); // Green if successful
      } else {
        stroke(255, 0, 0, 192); // Red if not successful
      }
    } else {
      stroke(128, 128, 128, 128);
    }
    rect(0, 0, d.z, d.z);
    popMatrix();
  }

  pushMatrix();
  translate(logoX, logoY);
  rotate(radians(logoRotation));
  noStroke();
  fill(60, 60, 192, 192);
  rect(0, 0, logoZ, logoZ);
  popMatrix();

  fill(255);
  scaffoldControlLogic();
  text("Trial " + (trialIndex + 1) + " of " + trialCount, width / 2, inchToPix(.8f));
}

void scaffoldControlLogic() {}

void mousePressed() {
  if (startTime == 0) {
    startTime = millis();
    println("time started!");
  }
}

void mouseReleased() {  
  if (dist(width / 2, height / 2, mouseX, mouseY) < inchToPix(3f)) {
    if (!userDone && !checkForSuccess())
      errorCount++;

    trialIndex++;

    if (trialIndex == trialCount && !userDone) {
      userDone = true;
      finishTime = millis();
    }
  }
}

boolean checkForSuccess() {
  Destination d = destinations.get(trialIndex);  
  boolean closeDist = dist(d.x, d.y, logoX, logoY) < inchToPix(.2f);
  boolean closeRotation = calculateDifferenceBetweenAngles(d.rotation, logoRotation) <= 10;
  boolean closeZ = abs(d.z - logoZ) < inchToPix(.2f); 

  return closeDist && closeRotation && closeZ;
}

double calculateDifferenceBetweenAngles(float a1, float a2) {
  double diff = abs(a1 - a2);
  diff %= 90;
  return diff > 45 ? 90 - diff : diff;
}

float inchToPix(float inch) {
  return inch * screenPPI;
}

class UDPReceiver extends Thread {
  DatagramSocket socket;
  boolean isPosition;

  UDPReceiver(int port, boolean isPosition) {
    this.isPosition = isPosition;
    try {
      socket = new DatagramSocket(port);
      println("UDP Receiver started on port " + port);
    } catch (SocketException e) {
      e.printStackTrace();
    }
  }

  public void run() {
    byte[] buffer = new byte[1024];
    while (true) {
      DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
      try {
        socket.receive(packet);
        String command = new String(packet.getData(), 0, packet.getLength()).trim();
        println("Received command: " + command);
        processCommand(command, isPosition);
      } catch (IOException e) {
        e.printStackTrace();
      }
    }
  }
}

void processCommand(String cmd, boolean isPosition) {
  // Base modify speed (FAST)
  //float baseMovementSpeed = inchToPix(.2f);
  //float baseRotationSpeed = 2.0f;
  //float baseScaleSpeed = inchToPix(.12f);
  float baseMovementSpeed = inchToPix(.1f);
  float baseRotationSpeed = 1.0f;
  float baseScaleSpeed = inchToPix(.05f);

  // Check if logo is near the target
  Destination target = destinations.get(trialIndex);
  //float distanceToTarget = dist(logoX, logoY, target.x, target.y);
  //float rotationDifference = abs(logoRotation - target.rotation);
  //float sizeDifference = abs(logoZ - target.z);

  // Reduce speed if close to the target (SLOW) FORBID!!!
  float slowFactor_dis = 1.0;
  float slowFactor_rot = 1.0;
  float slowFactor_siz = 1.0;
  //if (distanceToTarget < inchToPix(.5f)) slowFactor_dis = 0.12;
  //if (rotationDifference < 10) slowFactor_rot = 0.2;
  //if (sizeDifference < inchToPix(.5f)) slowFactor_siz = 0.2;
  float movementSpeed = baseMovementSpeed * slowFactor_dis;
  float rotationSpeed = baseRotationSpeed * slowFactor_rot;
  float scaleSpeed = baseScaleSpeed * slowFactor_siz;

  if (isPosition) {
    if (cmd.equals("A")) logoX -= movementSpeed;
    else if (cmd.equals("D")) logoX += movementSpeed;
    else if (cmd.equals("W")) logoY -= movementSpeed;
    else if (cmd.equals("S")) logoY += movementSpeed;
  } else {
    if (cmd.equals("L")) logoRotation -= rotationSpeed;
    else if (cmd.equals("R")) logoRotation += rotationSpeed;
    else if (cmd.equals("-")) logoZ = constrain(logoZ - scaleSpeed, .01, inchToPix(4f));
    else if (cmd.equals("+")) logoZ = constrain(logoZ + scaleSpeed, .01, inchToPix(4f));
  }
}