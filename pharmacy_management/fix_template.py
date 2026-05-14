import os

file_path = 'templates/pharmacy/upload_prescription.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix newline issues in template tags
content = content.replace('style="display:none;"\n                        {% endif %}', 'style="display:none;"{% endif %}')
content = content.replace('style="display:none;" {% endif %}', 'style="display:none;"{% endif %}')
content = content.replace('{% if not medicine or\n                                medicine.prescription_required %}', '{% if not medicine or medicine.prescription_required %}')
content = content.replace('{% if not medicine or\n                            medicine.prescription_required %}', '{% if not medicine or medicine.prescription_required %}')
content = content.replace('<i\n                        class="fas', '<i class="fas')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
