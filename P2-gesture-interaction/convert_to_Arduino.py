import tensorflow as tf
import keras

# 加载你的Keras模型
model = keras.models.load_model('models/model_Hybrid_bonus.keras')

# 将模型转换为.tflite格式
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# 保存.tflite文件
with open("gesture_model.tflite", "wb") as f:
    f.write(tflite_model)
