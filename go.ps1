ffmpeg -ss 21 -t 16 -i "D:\Golden_Wings_August_2025.mp4" -vf 'select=not(mod(n\,12)),scale=320:-1:flags=lanczos,tile=8x4:padding=4:margin=4' -q:v2-frames:v 1 -y "C:\Users\nobby.ONETRUESLAYSTAT\Documents\golden-wings-search\contact_sheets\Golden_Wings_August_2025_21s_16s_every12f.jpg"

ffmpeg -ss 21 -t 16 -i "D:\Golden_Wings_August_2025.mp4" -vf 'select=not(mod(n\,12)),scale=320:-1:flags=lanczos,tile=8x4:padding=4:margin=4' -q:v2-frames:v 1 -y "C:\Users\nobby.ONETRUESLAYSTAT\Documents\golden-wings-search\contact_sheets\Golden_Wings_August_2025_21s_16s_every12f.jpg"
