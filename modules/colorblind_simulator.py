from PIL import Image
import numpy as np
MATRICES = {
    "protanopia": np.array([[0.567,0.433,0.0],[0.558,0.442,0.0],[0.0,0.242,0.758]]),
    "deuteranopia": np.array([[0.625,0.375,0.0],[0.7,0.3,0.0],[0.0,0.3,0.7]]),
    "tritanopia": np.array([[0.95,0.05,0.0],[0.0,0.433,0.567],[0.0,0.475,0.525]])
}
def simulate_and_save(pil_image, out_base):
    img = pil_image.convert('RGB')
    arr = np.array(img)
    paths = {}
    for name, mat in MATRICES.items():
        flat = arr.reshape(-1,3).astype(float)/255.0
        transformed = (flat @ mat.T)
        transformed = (np.clip(transformed,0,1)*255).astype('uint8').reshape(arr.shape)
        out = Image.fromarray(transformed)
        path = f"{out_base}_{name}.png"
        out.save(path)
        paths[name] = path
    return paths
