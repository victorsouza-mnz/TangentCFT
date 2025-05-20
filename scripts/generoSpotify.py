import json
import time
import requests
import base64
import os


# Function to sleep and create delay
def sleep(ms):
    time.sleep(ms / 1000)  # Convert ms to seconds


# Function to make HTTP request with Promise
def http_request(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


# Function to obtain token
def obter_token_spotify():
    client_id = "366e6fcbacf34baca211659e72a742bd"
    client_secret = "5b992efd1c27484f8abefbd45a74c49c"
    encoded_credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode("utf-8")
    ).decode("utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        response.raise_for_status()


# Function to process an artist
def processar_artista(artista, token):
    nome = artista["ArtistName"]

    resultado = {
        "ArtistName": nome,
        "genero": "",
        "NomeSpotify": "",
    }

    if not nome:
        resultado["genero"] = "Nome vazio"
        return resultado

    try:
        # Search on Spotify
        url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(nome)}&type=artist&limit=1"
        headers = {"Authorization": f"Bearer {token}"}

        data = http_request(url, headers)
        artista_spotify = (
            data["artists"]["items"][0] if data["artists"]["items"] else None
        )

        if artista_spotify:
            resultado["genero"] = (
                ", ".join(artista_spotify["genres"])
                if artista_spotify["genres"]
                else "Sem gêneros"
            )
            resultado["NomeSpotify"] = artista_spotify["name"]
        else:
            resultado["genero"] = "Gênero não encontrado"

        # Delay to avoid request limit
        sleep(250)  # 250ms between requests (allows up to 4 per second)
    except Exception as e:
        resultado["genero"] = "Erro ao buscar"
        print(f"Erro ao buscar artista {nome}: {str(e)}")

    return resultado


# Function to save results to a file
def salvar_resultados(resultados, nome_arquivo):
    resultados_json = json.dumps(resultados, indent=2)
    nome_saida = nome_arquivo.replace(".json", "") + "_com_generos.json"
    caminho_saida = os.path.join(os.getcwd(), nome_saida)

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(resultados_json)

    print(f"Resultados atualizados em: {caminho_saida} ({len(resultados)} artistas)")


# Function to load existing results
def carregar_resultados_existentes(nome_arquivo):
    nome_saida = nome_arquivo.replace(".json", "") + "_com_generos.json"
    caminho_saida = os.path.join(os.getcwd(), nome_saida)

    try:
        if os.path.exists(caminho_saida):
            with open(caminho_saida, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar resultados existentes, começando do zero: {str(e)}")

    return []


# Function to fetch genres from Spotify
def buscar_genero_spotify(nome_arquivo):
    try:
        # Read file
        print(f"Lendo arquivo: {nome_arquivo}")
        caminho_arquivo = os.path.join(os.getcwd(), nome_arquivo)

        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            artistas = json.load(f)

        if not isinstance(artistas, list):
            raise ValueError("O arquivo deve conter um array de artistas")

        # Load already processed results
        resultados = carregar_resultados_existentes(nome_arquivo)

        # Identify artists with errors and need to be reprocessed
        artistas_com_erro = [r for r in resultados if r["genero"] == "Erro ao buscar"]
        artistas_para_processar = [
            a
            for a in artistas
            if not any(
                r["ArtistGenre"] == a["ArtistGenre"] for r in resultados
            )  # New artists
            or any(
                e["ArtistGenre"] == a["ArtistGenre"] for e in artistas_com_erro
            )  # Artists with error
        ]

        print(f"Total de artistas: {len(artistas)}")
        print(f"Artistas já processados: {len(resultados)}")
        print(f"Artistas com erro para reprocessar: {len(artistas_com_erro)}")
        print(f"Total de artistas para processar: {len(artistas_para_processar)}")

        if len(artistas_para_processar) == 0:
            print("Todos os artistas já foram processados com sucesso!")
            return resultados

        # Get token
        print("Obtendo token...")
        token = obter_token_spotify()
        print("Token obtido com sucesso")

        # Process artists in batches of 5
        for i in range(0, len(artistas_para_processar), 5):
            lote = artistas_para_processar[i : i + 5]
            print(
                f"Processando lote {i // 5 + 1}, artistas {i + 1} até {min(i + 5, len(artistas_para_processar))}"
            )

            # Process batch in parallel
            resultados_lote = [processar_artista(artista, token) for artista in lote]

            # Update results
            for novo_resultado in resultados_lote:
                index = next(
                    (
                        index
                        for index, r in enumerate(resultados)
                        if r["ArtistGenre"] == novo_resultado["ArtistGenre"]
                    ),
                    -1,
                )
                if index != -1:
                    resultados[index] = novo_resultado  # Update existing result
                else:
                    resultados.append(novo_resultado)  # Add new result

            salvar_resultados(resultados, nome_arquivo)

        print(
            f"Processamento completo. Total de artistas processados: {len(resultados)}"
        )
        return resultados
    except Exception as e:
        print(f"Erro: {str(e)}")
        raise e


# Run the process
buscar_genero_spotify("csvjson.json")
