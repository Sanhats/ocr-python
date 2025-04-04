import requests
import json
import sys
import os

def test_analyze_skin_endpoint():
    try:
        # URL del endpoint
        url = 'http://127.0.0.1:8080/analyze_skin/'
        
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
        
        # Enviar la solicitud
        print(f'Enviando imagen a {url}...')
        response = requests.post(url, files=files, timeout=10)
        
        # Cerrar el archivo
        files['file'][1].close()
        
        # Mostrar resultados
        print(f'Status Code: {response.status_code}')
        if response.status_code == 200:
            result = response.json()
            print('Análisis de piel exitoso:')
            print(f'Estado: {result["status"]}')
            print('\nDatos del análisis:')
            print(f'Color promedio de piel (BGR): {result["data"]["average_skin_color"]}')
            print(f'Porcentaje de manchas: {result["data"]["spot_percentage"]*100:.2f}%')
            
            # Mostrar nuevos datos de análisis si están disponibles
            if "texture_analysis" in result["data"]:
                print('\nAnálisis de textura:')
                for key, value in result["data"]["texture_analysis"].items():
                    print(f'- {key}: {value:.4f}')
            
            if "skin_type" in result["data"]:
                print(f'\nTipo de piel: {result["data"]["skin_type"]}')
                
            if "brightness" in result["data"]:
                print(f'Brillo: {result["data"]["brightness"]:.2f}')
                
            return True
        else:
            print(f'Error en la respuesta: {response.text}')
            return False
            
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
    success = test_analyze_skin_endpoint()
    if not success:
        sys.exit(1)