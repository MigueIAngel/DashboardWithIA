from pathlib import Path
import json
from datetime import datetime
from collections import defaultdict
import re

class BuscadorCodeunit:  # *** CAMBIO: Renombrado de BuscadorTableExt a BuscadorCodeunit
    def __init__(self, carpeta_repositorios):
        self.carpeta_repositorios = Path(carpeta_repositorios)
        self.archivos_encontrados = {}
        self.archivos_repetidos = {}
        self.archivos_unicos = {}
        self.todos_los_procedures = {}  # *** CAMBIO: De todos_los_campos a todos_los_procedures
        self.errores = []

    def buscar_archivos(self):
        """Busca archivos Codeunit.al en todos los repositorios"""  # *** CAMBIO: Documentación actualizada
        if not self.carpeta_repositorios.exists():
            raise FileNotFoundError(f"La carpeta {self.carpeta_repositorios} no existe")

        for repo_path in self.carpeta_repositorios.iterdir():
            if repo_path.is_dir():
                try:
                    self._procesar_repositorio(repo_path)
                except Exception as e:
                    self.errores.append(f"Error en {repo_path.name}: {str(e)}")
                    print(f"❌ Error procesando {repo_path.name}: {e}")

    def _procesar_repositorio(self, repo_path):
        """Procesa un repositorio individual"""
        repo_name = repo_path.name
        print(f"🔍 Procesando repositorio: {repo_name}")
        archivos_repo = []

        for llb_path in repo_path.rglob("LLB"):
            if llb_path.is_dir():
                print(f"  📁 Encontrada carpeta LLB: {llb_path.relative_to(repo_path)}")
                
                # *** CAMBIO PRINCIPAL: Buscar .Codeunit.al en lugar de .TableExt.al ***
                for archivo in llb_path.rglob("*.CodeUnit.al"):
                    carpeta_llb_completa = str(llb_path.relative_to(repo_path))
                    
                    if archivo.parent != llb_path:
                        subcarpeta = str(archivo.parent.relative_to(llb_path))
                        carpeta_llb_completa = f"{carpeta_llb_completa}/{subcarpeta}"

                    archivos_repo.append({
                        'ruta_completa': str(archivo),
                        'ruta_relativa': str(archivo.relative_to(repo_path)),
                        'ruta_desde_llb': str(archivo.relative_to(llb_path)),
                        'carpeta_llb_base': carpeta_llb_completa,
                        'nombre': archivo.name,
                        'tamaño': archivo.stat().st_size,
                        'modificado': datetime.fromtimestamp(archivo.stat().st_mtime).isoformat()
                    })
                    print(f"    ✅ {archivo.relative_to(llb_path)} ({archivo.name})")

        if archivos_repo:
            self.archivos_encontrados[repo_name] = archivos_repo
            print(f"  📊 Total archivos encontrados: {len(archivos_repo)}")
        else:
            print(f"  ⚠️ No se encontraron archivos Codeunit.al")  # *** CAMBIO: Mensaje actualizado

    def filtrar_archivos_repetidos(self):
        """Filtra archivos que aparecen en al menos 2 carpetas LLB distintas"""
        print("\n🔍 Filtrando archivos repetidos...")
        archivos_por_nombre = defaultdict(list)

        for repo, archivos in self.archivos_encontrados.items():
            for archivo in archivos:
                carpeta_llb_id = f"{repo}/{archivo['carpeta_llb_base']}"
                archivos_por_nombre[archivo['nombre']].append({
                    'archivo': archivo,
                    'repo': repo,
                    'carpeta_llb_id': carpeta_llb_id
                })

        archivos_filtrados = {}
        archivos_unicos = {}

        for nombre_archivo, apariciones in archivos_por_nombre.items():
            carpetas_unicas = set(aparicion['carpeta_llb_id'] for aparicion in apariciones)
            repositorios_unicos = set(aparicion['repo'] for aparicion in apariciones)

            if len(carpetas_unicas) > 1:
                archivos_filtrados[nombre_archivo] = {
                    'total_apariciones': len(apariciones),
                    'carpetas_llb': list(carpetas_unicas),
                    'repositorios': list(repositorios_unicos),
                    'archivos': apariciones
                }
                print(f"  ✅ {nombre_archivo} - encontrado en {len(carpetas_unicas)} carpetas LLB distintas")
            else:
                print(f"  ❌ {nombre_archivo} - solo en 1 carpeta LLB, descartado")
                archivos_unicos[nombre_archivo] = {
                    'total_apariciones': len(apariciones),
                    'carpetas_llb': list(carpetas_unicas),
                    'repositorios': list(repositorios_unicos),
                    'archivos': apariciones
                }

        self.archivos_repetidos = archivos_filtrados
        self.archivos_unicos = archivos_unicos
        return archivos_filtrados, archivos_unicos

    def extraer_procedures_de_archivo(self, ruta_archivo):
        """Extrae los procedures de un archivo .Codeunit.al"""  # *** CAMBIO: Nueva función para procedures
        procedures = {}
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                lineas = contenido.split('\n')
                
                for numero_linea, linea in enumerate(lineas, 1):
                    linea_limpia = linea.strip()
                    
                    # *** CAMBIO PRINCIPAL: Buscar patterns de procedure ***
                    # Patrones para capturar diferentes tipos de procedures:
                    # - procedure NombreProcedure()
                    # - local procedure NombreProcedure()
                    # - internal procedure NombreProcedure()
                    # - procedure NombreProcedure(params): ReturnType
                    
                    patron_procedure = r'^\s*(local\s+|internal\s+)?procedure\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
                    match = re.search(patron_procedure, linea_limpia, re.IGNORECASE)
                    
                    if match:
                        # Extraer el modificador (local, internal) y el nombre del procedure
                        modificador = match.group(1).strip() if match.group(1) else "public"
                        nombre_procedure = match.group(2)
                        
                        # Limpiar modificador
                        if modificador and modificador.lower() in ['local', 'internal']:
                            modificador = modificador.lower()
                        else:
                            modificador = "public"
                        
                        # Crear clave única incluyendo el modificador para diferenciar procedures con mismo nombre
                        clave_procedure = f"{nombre_procedure}"
                        
                        # Si ya existe, agregar sufijo para diferenciar
                        contador = 1
                        clave_original = clave_procedure
                        while clave_procedure in procedures:
                            contador += 1
                            clave_procedure = f"{clave_original}_{contador}"
                        
                        procedures[clave_procedure] = {
                            'linea': linea_limpia,
                            'numero_linea': numero_linea,
                            'nombre': nombre_procedure,
                            'modificador': modificador,
                            'linea_completa': linea_limpia
                        }

        except Exception as e:
            print(f"❌ Error leyendo archivo {ruta_archivo}: {e}")
            self.errores.append(f"Error leyendo {ruta_archivo}: {e}")

        return procedures

    def analizar_todos_los_procedures(self):
        """Analiza TODOS los procedures y determina si se repiten o son únicos"""  # *** CAMBIO: Renombrado
        print("\n🔍 Analizando TODOS los procedures...")

        # Primero, extraer todos los procedures de todos los archivos
        todos_los_procedures_global = defaultdict(lambda: defaultdict(list))

        # Procesar archivos únicos
        for nombre_archivo, info in self.archivos_unicos.items():
            print(f"\n📄 Procesando {nombre_archivo}...")
            for archivo_info in info['archivos']:
                ruta = archivo_info['archivo']['ruta_completa']
                repo = archivo_info['repo']
                print(f"  📁 Extrayendo procedures de {repo}...")
                
                procedures = self.extraer_procedures_de_archivo(ruta)  # *** CAMBIO: Llamar nueva función
                
                for nombre_procedure, info_procedure in procedures.items():
                    todos_los_procedures_global[nombre_archivo][nombre_procedure].append({
                        'repositorio': repo,
                        'linea': info_procedure['linea'],
                        'numero_linea': info_procedure['numero_linea'],
                        'ruta_archivo': ruta,
                        'modificador': info_procedure['modificador'],
                        'nombre': info_procedure['nombre']
                    })

        # Procesar archivos repetidos
        for nombre_archivo, info in self.archivos_repetidos.items():
            print(f"\n📄 Procesando {nombre_archivo}...")
            for archivo_info in info['archivos']:
                ruta = archivo_info['archivo']['ruta_completa']
                repo = archivo_info['repo']
                print(f"  📁 Extrayendo procedures de {repo}...")
                
                procedures = self.extraer_procedures_de_archivo(ruta)  # *** CAMBIO: Llamar nueva función
                
                for nombre_procedure, info_procedure in procedures.items():
                    todos_los_procedures_global[nombre_archivo][nombre_procedure].append({
                        'repositorio': repo,
                        'linea': info_procedure['linea'],
                        'numero_linea': info_procedure['numero_linea'],
                        'ruta_archivo': ruta,
                        'modificador': info_procedure['modificador'],
                        'nombre': info_procedure['nombre']
                    })

        # Procesar y clasificar cada procedure
        resultado_final = {}

        for nombre_archivo, procedures_del_archivo in todos_los_procedures_global.items():
            resultado_final[nombre_archivo] = {}

            for nombre_procedure, apariciones in procedures_del_archivo.items():
                repositorios_unicos = set(aparicion['repositorio'] for aparicion in apariciones)

                if len(repositorios_unicos) > 1:
                    # Procedure repetido
                    resultado_final[nombre_archivo][nombre_procedure] = {
                        'estado': 'REPETIDO',
                        'repositorios': list(repositorios_unicos),
                        'total_repositorios': len(repositorios_unicos),
                        'apariciones': apariciones
                    }
                else:
                    # Procedure único
                    resultado_final[nombre_archivo][nombre_procedure] = {
                        'estado': 'ÚNICO',
                        'repositorios': list(repositorios_unicos),
                        'total_repositorios': 1,
                        'apariciones': apariciones
                    }

        self.todos_los_procedures = resultado_final  # *** CAMBIO: Asignar a todos_los_procedures
        return resultado_final

    def mostrar_todos_los_procedures(self):
        """Muestra TODOS los procedures clasificados por repetidos/únicos"""  # *** CAMBIO: Renombrado
        print("\n" + "="*100)
        print("📋 TODOS LOS PROCEDURES - REPETIDOS Y ÚNICOS")  # *** CAMBIO: Título actualizado
        print("="*100)

        if not self.todos_los_procedures:  # *** CAMBIO: Variable actualizada
            print("⚠️ No se encontraron procedures")  # *** CAMBIO: Mensaje actualizado
            return

        total_procedures = 0  # *** CAMBIO: Variable renombrada
        procedures_repetidos = 0  # *** CAMBIO: Variable renombrada
        procedures_unicos = 0  # *** CAMBIO: Variable renombrada

        for nombre_archivo, procedures in self.todos_los_procedures.items():  # *** CAMBIO: Variable actualizada
            print(f"\n📄 {nombre_archivo}")
            print(f"  Total procedures: {len(procedures)}")  # *** CAMBIO: Mensaje actualizado

            # Separar procedures repetidos y únicos
            repetidos = {k: v for k, v in procedures.items() if v['estado'] == 'REPETIDO'}
            unicos = {k: v for k, v in procedures.items() if v['estado'] == 'ÚNICO'}

            # Mostrar procedures repetidos
            if repetidos:
                print(f"\n  🔄 PROCEDURES REPETIDOS ({len(repetidos)}):")  # *** CAMBIO: Mensaje actualizado
                for nombre_procedure, info in repetidos.items():
                    print(f"\n    📌 {nombre_procedure}")
                    print(f"      Estado: {info['estado']}")
                    print(f"      Repositorios: {', '.join(info['repositorios'])}")
                    print(f"      Total repositorios: {info['total_repositorios']}")
                    for aparicion in info['apariciones']:
                        modificador_str = f"[{aparicion['modificador']}] " if aparicion['modificador'] != 'public' else ""
                        print(f"      {aparicion['repositorio']}: {modificador_str}{aparicion['linea']}")

            # Mostrar procedures únicos
            if unicos:
                print(f"\n  ⭐ PROCEDURES ÚNICOS ({len(unicos)}):")  # *** CAMBIO: Mensaje actualizado
                for nombre_procedure, info in unicos.items():
                    print(f"\n    📌 {nombre_procedure}")
                    print(f"      Estado: {info['estado']}")
                    print(f"      Repositorio: {info['repositorios'][0]}")
                    aparicion = info['apariciones'][0]
                    modificador_str = f"[{aparicion['modificador']}] " if aparicion['modificador'] != 'public' else ""
                    print(f"      Línea: {modificador_str}{aparicion['linea']}")

            total_procedures += len(procedures)  # *** CAMBIO: Variable actualizada
            procedures_repetidos += len(repetidos)  # *** CAMBIO: Variable actualizada
            procedures_unicos += len(unicos)  # *** CAMBIO: Variable actualizada

        print(f"\n" + "="*100)
        print(f"📊 RESUMEN GENERAL:")
        print(f"  Total procedures analizados: {total_procedures}")  # *** CAMBIO: Mensaje actualizado
        print(f"  Procedures repetidos: {procedures_repetidos}")  # *** CAMBIO: Mensaje actualizado
        print(f"  Procedures únicos: {procedures_unicos}")  # *** CAMBIO: Mensaje actualizado
        print("="*100)

    def guardar_resumen_completo(self, archivo_salida="resumen_codeunits_completo.json"):  # *** CAMBIO: Nombre de archivo
        """Guarda resumen completo incluyendo todos los procedures"""  # *** CAMBIO: Documentación
        resumen = {
            'fecha_busqueda': datetime.now().isoformat(),
            'tipo_analisis': 'codeunits',  # *** CAMBIO: Agregar tipo de análisis
            'estadisticas': {
                'total_repositorios': len(self.archivos_encontrados),
                'total_archivos': sum(len(archivos) for archivos in self.archivos_encontrados.values()),
                'archivos_repetidos': len(self.archivos_repetidos),
                'total_procedures': sum(len(procedures) for procedures in self.todos_los_procedures.values()),  # *** CAMBIO: Variable actualizada
                'procedures_repetidos': sum(1 for procedures in self.todos_los_procedures.values()  # *** CAMBIO: Variable actualizada
                                          for procedure in procedures.values() if procedure['estado'] == 'REPETIDO'),
                'procedures_unicos': sum(1 for procedures in self.todos_los_procedures.values()  # *** CAMBIO: Variable actualizada
                                       for procedure in procedures.values() if procedure['estado'] == 'ÚNICO')
            },
            'todos_los_archivos': self.archivos_encontrados,
            'archivos_repetidos': self.archivos_repetidos,
            'archivos_unicos': self.archivos_unicos,
            'todos_los_procedures': self.todos_los_procedures,  # *** CAMBIO: Variable actualizada
            'errores': self.errores
        }

        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(resumen, f, indent=2, ensure_ascii=False)

        print(f"💾 Resumen completo guardado en: {archivo_salida}")

    def obtener_todos_los_procedures(self):  # *** CAMBIO: Renombrado
        """Retorna todos los procedures clasificados"""
        return self.todos_los_procedures  # *** CAMBIO: Variable actualizada


# Uso del script completo
if __name__ == "__main__":
    # Configuración
    ruta_repositorios = "/Users/miguelangel/Documents/AL"

    # Crear instancia del buscador
    buscador = BuscadorCodeunit(ruta_repositorios)  # *** CAMBIO: Nueva clase

    # PASO 1: Buscar archivos
    print("🚀 PASO 1: Buscando archivos Codeunit.al...")  # *** CAMBIO: Mensaje actualizado
    buscador.buscar_archivos()

    # PASO 2: Filtrar archivos repetidos
    print("\n🚀 PASO 2: Filtrando archivos repetidos...")
    archivos_repetidos, archivos_unicos = buscador.filtrar_archivos_repetidos()

    # PASO 3: Analizar TODOS los procedures
    print("\n🚀 PASO 3: Analizando TODOS los procedures...")  # *** CAMBIO: Mensaje actualizado
    todos_los_procedures = buscador.analizar_todos_los_procedures()  # *** CAMBIO: Llamada actualizada

    # PASO 4: Mostrar TODOS los procedures
    print("\n🚀 PASO 4: Mostrando TODOS los procedures...")  # *** CAMBIO: Mensaje actualizado
    buscador.mostrar_todos_los_procedures()  # *** CAMBIO: Llamada actualizada

    # PASO 5: Guardar resumen
    print("\n🚀 PASO 5: Guardando resumen...")
    buscador.guardar_resumen_completo()

    print(f"\n🎉 ¡Análisis completo de Codeunits terminado!")  # *** CAMBIO: Mensaje actualizado
