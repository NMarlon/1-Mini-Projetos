import os
from PIL import Image

input_folder = "./minhas_imagens"
output_folder = "./stickers_webp"
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        filepath = os.path.join(input_folder, filename)
        with Image.open(filepath) as img:
            # Preserva a proporção e adiciona num quadrado 512x512
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            # Centraliza a imagem no canvas
            offset = ((512 - img.width) // 2, (512 - img.height) // 2)
            canvas.paste(img, offset)
            
            # Salva como WEBP otimizado
            out_name = os.path.splitext(filename)[0] + ".webp"
            canvas.save(os.path.join(output_folder, out_name), "WEBP", quality=85)

print("100 figurinhas processadas e prontas!") 