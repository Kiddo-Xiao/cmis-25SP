#include <Arduino_BMI270_BMM150.h>
#include <ArduTFLite.h>
#include "gesture_model.h"


const int numSamples = 50;   // 滑动窗口大小
const int numChannels = 6;
const int predictionInterval = 10; // 每隔10个样本进行一次预测

const int LABELNUM = 9;
// const int LABELNUM = 5;
const char* GESTURES[] = {"b", "c", "e", "f", "l", "o", "r", "u", "x"};
// const char* GESTURES[] = {"b", "l", "o", "r", "u"};

// 预测结果到按键的映射
const char* predictionMap[] = {"S", "_", "_", "_", "A", "_", "D", "W", "_"};
// const char* predictionMap[] = {"S", "A", "-", "D", "W"};


// 滑动窗口缓冲区
float slidingWindow[numSamples][numChannels] = {0};
int samplesCollected = 0;

// 模型内存空间
constexpr int tensorArenaSize = 12 * 1024; // 12KB足够
alignas(16) byte tensorArena[tensorArenaSize];

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }

  if (!modelInit(gesture_model, tensorArena, sizeof(tensorArena))) {
    Serial.println("Model initialization failed!");
    while (1);
  }

  Serial.println("Setup complete, starting gesture detection...");
}

void loop() {
    float aX, aY, aZ, gX, gY, gZ;

    if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
      IMU.readAcceleration(aX, aY, aZ);
      IMU.readGyroscope(gX, gY, gZ);


      // 数据预处理
      aX /= 4.0;
      aY /= 4.0;
      aZ /= 4.0;
      gX /= 4000.0;
      gY /= 4000.0;
      gZ /= 4000.0;

      // 滑动窗口更新
      memmove(slidingWindow, slidingWindow[1], sizeof(slidingWindow) - sizeof(slidingWindow[0]));
      slidingWindow[numSamples - 1][0] = aX;
      slidingWindow[numSamples - 1][1] = aY;
      slidingWindow[numSamples - 1][2] = aZ;
      slidingWindow[numSamples - 1][3] = gX;
      slidingWindow[numSamples - 1][4] = gY;
      slidingWindow[numSamples - 1][5] = gZ;

      samplesCollected++;

      // 每10个数据进行一次预测
      if (samplesCollected >= numSamples && samplesCollected % 10 == 0) {
        for (int i = 0; i < numSamples; i++) {
          for (int j = 0; j < numChannels; j++) {
            modelSetInput(slidingWindow[i][j], i * numChannels + j);
          }
        }

        if (!modelRunInference()) {
          Serial.println("Inference error!");
        }

        // 获取预测结果
        float maxProb = 0;
        int detectedGesture = -1;

        for (int i = 0; i < LABELNUM; i++) {
          float prob = modelGetOutput(i);
          if (prob > maxProb) {
            maxProb = prob;
            detectedGesture = i;
          }
        }

        // 串口输出预测结果
        if (GESTURES[detectedGesture] != "o"){
          const char* key = predictionMap[detectedGesture];
          if (key != "_") {
            // udp.beginPacket(udpAddress, udpPort);
            // udp.write((uint8_t*)key, strlen(key));
            // udp.endPacket();
            // Serial.print("Key: ");
            Serial.println(key);
            // Serial.print(" (");
            // Serial.print(maxProb * 100, 2);
            // Serial.println("%)");
            
          }
        }
      }
    }
          
}