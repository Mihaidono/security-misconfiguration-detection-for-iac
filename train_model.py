import joblib
import pickle
from sklearn.feature_extraction import DictVectorizer

from tensorflow.python.keras import layers, models, optimizers

# 1. Load Training Data
print("Loading data...")
# Ensure training_data.pkl exists in the same directory
try:
    with open("training_data.pkl", "rb") as f:
        train_data = pickle.load(f)
except FileNotFoundError:
    print("Error: 'training_data.pkl' not found. Run the data loader first.")
    exit()

# 2. Vectorize
# sparse=False is important for Deep Learning inputs (Dense layers expect arrays, not sparse matrices)
vec = DictVectorizer(sparse=False)
X = vec.fit_transform(train_data)

# Save the vectorizer so the scanner uses the exact same mapping
joblib.dump(vec, "vectorizer.pkl")

# 3. Build Autoencoder
# Architecture: Input -> Compress -> Bottleneck -> Expand -> Output
input_dim = X.shape[1]
encoding_dim = 32  # Compressed representation size

# FIX: Use 'layers' and 'models' from the imports above
input_layer = layers.Input(shape=(input_dim,))

# Encoder
encoder = layers.Dense(128, activation="relu")(input_layer)
encoder = layers.Dropout(0.2)(encoder)
encoder = layers.Dense(encoding_dim, activation="relu")(encoder)

# Decoder
decoder = layers.Dense(128, activation="relu")(encoder)
decoder = layers.Dense(input_dim, activation="sigmoid")(decoder)

# Model
autoencoder = models.Model(inputs=input_layer, outputs=decoder)

# Compile
autoencoder.compile(optimizer=optimizers.Adam(learning_rate=0.001), loss="mse")

# 4. Train
print("Training Model...")
autoencoder.fit(X, X, epochs=50, batch_size=16, shuffle=True, verbose=1)

# Save the model
autoencoder.save("tf_security_model.h5")
print("Model Saved!")
