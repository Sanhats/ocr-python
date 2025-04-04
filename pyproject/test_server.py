import requests
import json
import sys

def test_root_endpoint():
    try:
        print('Intentando conectar a http://127.0.0.1:8080...')
        response = requests.get('http://127.0.0.1:8080', timeout=5)
        print(f'Status Code: {response.status_code}')
        print(f'Response: {json.dumps(response.json(), indent=2)}')
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
    success = test_root_endpoint()
    if not success:
        sys.exit(1)