import google.generativeai as genai
import streamlit as st
from typing import Optional
import os

class AIHelper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self._configure_ai()
    
    def _configure_ai(self):
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        except Exception as e:
            st.error(f"Error al configurar IA: {str(e)}")
            self.model = None
    
    def leer_contenido_archivo(self, ruta_archivo: str) -> Optional[str]:
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                return archivo.read()
        except Exception as e:
            print(f"Error leyendo archivo {ruta_archivo}: {str(e)}")
            return None
    
    def get_procedure_analysis(self, nombre_procedure: str, linea_procedure: str, ruta_archivo: str = None, numero_linea: int = None) -> str:
        
        if not self.model:
            return "❌ IA no disponible"
        
        try:
            contexto_basico = f"Procedure: {linea_procedure}"
            
            contexto_adicional = ""
            if ruta_archivo and numero_linea:
                contenido_archivo = self.leer_contenido_archivo(ruta_archivo)
                if contenido_archivo:
                    lineas = contenido_archivo.split('\n')
                    # Obtener algunas líneas del procedure (desde la línea del procedure hasta unas líneas después)
                    inicio = max(0, numero_linea - 1)  
                    fin = min(len(lineas), numero_linea + 100)  
                    
                    contexto_adicional = "\n".join(lineas[inicio:fin])
            
            if contexto_adicional:
                prompt = f"""Analiza este procedure de Business Central AL y describe brevemente qué hace en menos de 40 palabras:

Nombre: {nombre_procedure}
Línea: {linea_procedure}

Contexto del código:
{contexto_adicional[:500]}

Responde SOLO la funcionalidad, sin explicaciones técnicas adicionales."""
            else:
                prompt = f"""Basándote en esta línea de procedure de Business Central AL, describe brevemente qué hace en menos de 30 palabras:

{linea_procedure}

Responde SOLO la funcionalidad principal."""
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            return f"❌ Error: {str(e)[:50]}..."
    
    def get_code_analysis_from_file(self, ruta_archivo: str, nombre_archivo: str) -> str:
        """
        Analiza un archivo leyendo su contenido desde el disco
        
        Args:
            ruta_archivo (str): Ruta completa al archivo
            nombre_archivo (str): Nombre del archivo para contexto
            
        Returns:
            str: Análisis del código
        """
        if not self.model:
            return "❌ IA no disponible - Error de configuración"
        
        contenido = self.leer_contenido_archivo(ruta_archivo)
        
        if contenido is None:
            return f"❌ No se pudo leer el archivo: {ruta_archivo}"
        

        return self.get_code_analysis(nombre_archivo, contenido)
    
    def get_file_description(self, archivo: str, max_palabras: int = 50) -> str:
        if not self.model:
            return "❌ IA no disponible - Error de configuración"
        
        try:
            prompt = f"""Describe brevemente en menos de {max_palabras} palabras qué hace el archivo de código llamado '{archivo}'.
Enfócate en su funcionalidad principal y propósito.
Sé conciso y específico."""
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"❌ Error al generar descripción: {str(e)}"
    
    def get_code_analysis(self, archivo: str, contenido_codigo: Optional[str] = None) -> str:
        if not self.model:
            return "❌ IA no disponible - Error de configuración"
        
        try:
            if contenido_codigo:
                contenido_limitado = contenido_codigo[:2000] if len(contenido_codigo) > 2000 else contenido_codigo
                
                prompt = f"""Analiza este código del archivo '{archivo}' y describe brevemente su funcionalidad principal:

Código:
{contenido_codigo}

Respuesta en menos de 150 palabras."""
            else:
                prompt = f"""Basándote solo en el nombre del archivo '{archivo}', infiere y describe brevemente:

1. Su posible función principal
2. Propósito probable

Respuesta en menos de 80 palabras."""
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"❌ Error al generar análisis: {str(e)}"
    
    def is_available(self) -> bool:
        return self.model is not None

def create_ai_helper(api_key: str) -> AIHelper:
  
    return AIHelper(api_key)

def get_quick_description(archivo: str, api_key: str) -> str:
    ai_helper = AIHelper(api_key)
    return ai_helper.get_file_description(archivo)
