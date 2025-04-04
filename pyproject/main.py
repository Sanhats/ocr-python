from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import cv2
import numpy as np
import io
import os
import uuid
import tempfile
from datetime import datetime

# Para generar PDF
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Para visualizaciones
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Usar backend no interactivo

app = FastAPI()

# Crear directorio temporal para almacenar reportes PDF
REPORTS_DIR = os.path.join(tempfile.gettempdir(), "skin_analysis_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Diccionario para almacenar los reportes generados
reports_storage = {}

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_image(img):
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Get color histogram for skin tone analysis
    avg_color_per_row = np.average(img, axis=0)
    avg_color = np.average(avg_color_per_row, axis=0)
    
    # Spot detection using adaptive threshold
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, threshold = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY_INV)
    spot_percentage = float(np.sum(threshold == 255) / threshold.size)
    
    # Texture analysis using Haralick features
    # Simplify to just contrast and homogeneity for basic texture analysis
    texture_features = {}
    try:
        # Convert to grayscale if not already
        if len(img.shape) > 2:
            gray_for_texture = gray
        else:
            gray_for_texture = img
            
        # Calculate GLCM (Gray-Level Co-occurrence Matrix)
        glcm = cv2.resize(gray_for_texture, (50, 50))  # Resize for faster processing
        glcm = np.uint8(glcm)
        
        # Calculate standard deviation for roughness estimation
        texture_features['roughness'] = float(np.std(glcm))
        
        # Calculate local binary pattern for texture pattern
        from skimage.feature import local_binary_pattern
        radius = 3
        n_points = 8 * radius
        try:
            lbp = local_binary_pattern(glcm, n_points, radius, method='uniform')
            texture_features['pattern_uniformity'] = float(np.sum(lbp == 0) / lbp.size)
        except ImportError:
            # If skimage is not available
            texture_features['pattern_uniformity'] = 0.0
    except Exception as e:
        texture_features = {
            'roughness': 0.0,
            'pattern_uniformity': 0.0
        }
    
    # Skin type classification based on color
    # Using a simplified version of Fitzpatrick scale based on BGR values
    b, g, r = avg_color
    brightness = (int(r) + int(g) + int(b)) / 3
    
    # Simple classification based on brightness
    if brightness > 200:
        skin_type = "Type I - Very fair skin"
    elif brightness > 170:
        skin_type = "Type II - Fair skin"
    elif brightness > 140:
        skin_type = "Type III - Medium skin"
    elif brightness > 110:
        skin_type = "Type IV - Olive skin"
    elif brightness > 80:
        skin_type = "Type V - Brown skin"
    else:
        skin_type = "Type VI - Dark brown to black skin"
    
    return {
        "average_skin_color": avg_color.tolist(),
        "spot_percentage": spot_percentage,
        "texture_analysis": texture_features,
        "skin_type": skin_type,
        "brightness": float(brightness)
    }

@app.post("/analyze_skin/")
async def analyze_skin(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image in OpenCV format
        contents = await file.read()
        np_img = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        # Process the image
        analysis = process_image(img)
        
        # Generar reporte PDF
        report_id = generate_skin_analysis_report(analysis, img)

        return {
            "status": "success",
            "data": analysis,
            "report_id": report_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_skin_analysis_report(analysis_data, original_image):
    # Generar un ID único para el reporte
    report_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"skin_analysis_report_{timestamp}_{report_id[:8]}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    # Crear documento PDF
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Título
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=12
    )
    elements.append(Paragraph("Skin Analysis Report", title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Fecha y hora
    date_style = ParagraphStyle(
        'Date',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        spaceAfter=12
    )
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Guardar imagen original y procesada para incluir en el reporte
    img_path = os.path.join(REPORTS_DIR, f"original_{report_id}.jpg")
    cv2.imwrite(img_path, original_image)
    
    # Añadir imagen original
    elements.append(Paragraph("Original Image", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    img = RLImage(img_path, width=4*inch, height=3*inch)
    elements.append(img)
    elements.append(Spacer(1, 0.25*inch))
    
    # Crear visualización de manchas
    gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, threshold = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY_INV)
    
    # Guardar imagen de manchas
    spots_img_path = os.path.join(REPORTS_DIR, f"spots_{report_id}.jpg")
    cv2.imwrite(spots_img_path, threshold)
    
    # Añadir imagen de manchas
    elements.append(Paragraph("Spot Detection", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    spots_img = RLImage(spots_img_path, width=4*inch, height=3*inch)
    elements.append(spots_img)
    elements.append(Spacer(1, 0.25*inch))
    
    # Crear gráfico de color de piel
    color_chart_path = os.path.join(REPORTS_DIR, f"color_chart_{report_id}.png")
    plt.figure(figsize=(4, 2))
    b, g, r = analysis_data["average_skin_color"]
    plt.bar(['Blue', 'Green', 'Red'], [b, g, r], color=['blue', 'green', 'red'])
    plt.title('Average Skin Color (BGR)')
    plt.savefig(color_chart_path)
    plt.close()
    
    # Añadir gráfico de color
    elements.append(Paragraph("Skin Color Analysis", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    color_chart = RLImage(color_chart_path, width=4*inch, height=2*inch)
    elements.append(color_chart)
    elements.append(Spacer(1, 0.25*inch))
    
    # Añadir resultados del análisis en formato de tabla
    elements.append(Paragraph("Analysis Results", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    
    # Crear tabla de resultados
    data = [
        ["Parameter", "Value"],
        ["Skin Type", analysis_data["skin_type"]],
        ["Brightness", f"{analysis_data['brightness']:.2f}"],
        ["Spot Percentage", f"{analysis_data['spot_percentage']*100:.2f}%"],
    ]
    
    # Añadir datos de textura
    for key, value in analysis_data["texture_analysis"].items():
        data.append([f"Texture: {key.capitalize()}", f"{value:.4f}"])
    
    # Estilo de tabla
    table = Table(data, colWidths=[2.5*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
    ]))
    elements.append(table)
    
    # Añadir recomendaciones basadas en el análisis
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph("Recommendations", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    
    # Generar recomendaciones basadas en el tipo de piel y otros factores
    recommendations = get_recommendations(analysis_data)
    for rec in recommendations:
        elements.append(Paragraph(f"• {rec}", styles['Normal']))
        elements.append(Spacer(1, 0.05*inch))
    
    # Construir el PDF
    doc.build(elements)
    
    # Limpiar archivos temporales de imágenes
    for temp_file in [img_path, spots_img_path, color_chart_path]:
        try:
            os.remove(temp_file)
        except:
            pass
    
    # Guardar referencia al reporte en el almacenamiento
    reports_storage[report_id] = {
        "filepath": filepath,
        "filename": filename,
        "created_at": datetime.now().isoformat(),
        "analysis_data": analysis_data
    }
    
    return report_id

def get_recommendations(analysis_data):
    """Genera recomendaciones basadas en los resultados del análisis"""
    recommendations = []
    
    # Recomendaciones basadas en el tipo de piel
    skin_type = analysis_data["skin_type"]
    if "Type I" in skin_type or "Type II" in skin_type:
        recommendations.append("Use sunscreen with SPF 50+ daily, even on cloudy days.")
        recommendations.append("Avoid prolonged sun exposure, especially between 10 AM and 4 PM.")
    elif "Type III" in skin_type or "Type IV" in skin_type:
        recommendations.append("Use sunscreen with SPF 30+ daily.")
        recommendations.append("Limit sun exposure during peak hours.")
    else:
        recommendations.append("Use sunscreen with SPF 15+ daily.")
    
    # Recomendaciones basadas en manchas
    spot_percentage = analysis_data["spot_percentage"]
    if spot_percentage > 0.05:
        recommendations.append("Consider products with ingredients like niacinamide or vitamin C to address hyperpigmentation.")
        recommendations.append("Consult a dermatologist for a personalized treatment plan for spots.")
    
    # Recomendaciones basadas en textura
    roughness = analysis_data["texture_analysis"].get("roughness", 0)
    if roughness > 20:
        recommendations.append("Use gentle exfoliants 1-2 times per week to improve skin texture.")
        recommendations.append("Consider adding a hydrating serum to your skincare routine.")
    
    # Recomendaciones generales
    recommendations.append("Maintain a consistent skincare routine with gentle cleansing twice daily.")
    recommendations.append("Stay hydrated by drinking plenty of water throughout the day.")
    
    return recommendations

@app.get("/download-report/{report_id}")
def download_report(report_id: str):
    # Verificar si el reporte existe
    if report_id not in reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report_info = reports_storage[report_id]
    filepath = report_info["filepath"]
    filename = report_info["filename"]
    
    # Verificar si el archivo existe
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    # Devolver el archivo PDF
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/pdf"
    )

@app.get("/")
def read_root():
    return {"message": "Skin Analysis API is running"}