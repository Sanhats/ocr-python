import requests
import json
import sys
import os
import time

def test_download_report():
    try:
        # Primero, analizar una imagen para obtener un report_id
        analyze_url = 'http://127.0.0.1:8080/analyze_skin/'
        
        # Buscar una imagen de prueba en el directorio actual
        test_images = [f for f in os.listdir('.') if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not test_images:
            print('No se encontraron imágenes de prueba en el directorio actual.')
            print('Por favor, coloca una imagen PNG o JPG en el directorio del proyecto.')
            return False
        
        # Usar la primera imagen encontrada
        test_image = test_images[0]
        print(f'Usando imagen de prueba: {test_image}')
        
        # Preparar el archivo para enviar
        files = {'file': (test_image, open(test_image, 'rb'), 'image/jpeg')}
        
        # Enviar la solicitud de análisis
        print(f'Enviando imagen a {analyze_url}...')
        response = requests.post(analyze_url, files=files, timeout=10)
        
        # Cerrar el archivo
        files['file'][1].close()
        
        if response.status_code != 200:
            print(f'Error en la respuesta del análisis: {response.text}')
            return False
            
        # Obtener el report_id
        result = response.json()
        if 'report_id' not in result:
            print('No se encontró report_id en la respuesta')
            return False
            
        report_id = result['report_id']
        print(f'ID del reporte generado: {report_id}')
        
        # Esperar un momento para asegurar que el reporte esté listo
        time.sleep(1)
        
        # Descargar el reporte
        download_url = f'http://127.0.0.1:8080/download-report/{report_id}'
        print(f'Descargando reporte desde {download_url}...')
        
        download_response = requests.get(download_url, timeout=10)
        
        if download_response.status_code != 200:
            print(f'Error al descargar el reporte: {download_response.text}')
            return False
            
        # Guardar el PDF descargado
        pdf_filename = f'downloaded_report_{report_id[:8]}.pdf'
        with open(pdf_filename, 'wb') as f:
            f.write(download_response.content)
            
        print(f'Reporte descargado y guardado como: {pdf_filename}')
        print('Prueba completada con éxito')
        return True
            
    except requests.exceptions.ConnectionError as ce:
        print(f'Error de conexión: {ce}')
        print('No se pudo conectar al servidor. Asegúrate de que el servidor esté corriendo.')
        return False
    except requests.exceptions.Timeout:
        print('Error: Tiempo de espera agotado al intentar conectar con el servidor.')
        return False
    except Exception as e:
        print(f'Error inesperado: {str(e)}')
        return False

if __name__ == '__main__':
    success = test_download_report()
    if not success:
        sys.exit(1)