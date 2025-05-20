from enum import Enum


class TupleTokenizationMode(Enum):
    """
    This enum shows how the tokenization of nodes should be done, given the node N!1234 for each of the enum values
    the outputs are:
    Tokenization type , tokens
    Value : 1234
    Type:   N!
    Both_Separated: N!, 1234
    Both_Non_Separated: N!1234
    """

    Value = 1
    Type = 2
    Both_Separated = 3
    Both_Non_Separated = 4


# Deprecated
class TupleEncoder:
    @staticmethod
    def encode_tuples(
        node_map,
        edge_map,
        node_id,
        edge_id,
        math_tuples,
        embedding_type=TupleTokenizationMode.Both_Separated,
        ignore_full_relative_path=True,
        tokenize_all=False,
        tokenize_number=True,
    ):
        """
        Takes the encoder map (which can be empty) and the last node id and enumerates the tuple tokens to converts the
        tuples to words (with n-gram as each tokenized tuple element) to make the formulas ready to be fed to fasttext
        :param edge_map: dictionary of tokens related to the path with between nodes in trees
        :param edge_id: the id of last edge token
        :param node_map: dictionary of tokens and their id
        :param node_id: the last node id
        :param math_tuples: list of formula tuples (which are extracted by Tangent-S) to be encoded
        :param embedding_type: one of the four possible tokenization model
        :param ignore_full_relative_path: determines to ignore the full relative path or not (default True)
        :param tokenize_all: determines to tokenize all elements (such as numbers and text) (default False)
        :param tokenize_number: determines to tokenize the numbers or not (default True)
        :return: list of encoded tuples
        """
        encoded_tuples = []
        update_map_node = {}
        update_map_edge = {}
        for math_tuple in math_tuples:
            encoded_tuple = ""
            tuple_elements = TupleEncoder.__get_tuple_elements(
                math_tuple, ignore_full_relative_path=ignore_full_relative_path
            )

            # Encoding Element 1
            converted_value, node_map, node_id, update_map_node = (
                TupleEncoder.__convert_node_elements(
                    tuple_elements[0],
                    node_map,
                    node_id,
                    update_map_node,
                    embedding_type,
                    tokenize_all=tokenize_all,
                    tokenize_number=tokenize_number,
                )
            )
            encoded_tuple = encoded_tuple + converted_value

            # Encoding Element 2
            converted_value, node_map, node_id, update_map_node = (
                TupleEncoder.__convert_node_elements(
                    tuple_elements[1],
                    node_map,
                    node_id,
                    update_map_node,
                    embedding_type,
                    tokenize_all=tokenize_all,
                    tokenize_number=tokenize_number,
                )
            )
            encoded_tuple = encoded_tuple + converted_value

            # Encoding Edge
            converted_value, edge_map, edge_id, update_map_edge = (
                TupleEncoder.__convert_path_elements(
                    tuple_elements[2], edge_map, edge_id, update_map_edge
                )
            )
            encoded_tuple = encoded_tuple + converted_value

            "Encode the full relative path"
            if not ignore_full_relative_path:
                converted_value, edge_map, edge_id, update_map_edge = (
                    TupleEncoder.__convert_path_elements(
                        tuple_elements[3], edge_map, edge_id, update_map_edge
                    )
                )
                encoded_tuple = encoded_tuple + converted_value
            encoded_tuples.append(encoded_tuple)

        return encoded_tuples, update_map_node, update_map_edge, node_id, edge_id

    @staticmethod
    def __convert_node_elements(
        node,
        node_map,
        node_id,
        update_map_node,
        embedding_type,
        tokenize_all=False,
        tokenize_number=False,
    ):
        lst = []
        if "!" in node:
            # This shows the tuple is a leaf in the tree and this node has only Type and no Value
            if node == "O!":
                lst.append(node)
            # Tuple has both Value and Type
            else:
                # All the node Type are kept with their ! sign.
                node_type = node.split("!")[0] + "!"
                # Value of the node
                node_value = node.split("!")[1]

                # Check if it needs to break down numbers or other Types such as text
                # For instance, convert "sin" to "s" "i" "n"
                if embedding_type == TupleTokenizationMode.Type:
                    lst.append(node_type)
                elif embedding_type == TupleTokenizationMode.Value:
                    if not tokenize_all and (not tokenize_number or node_type != "N!"):
                        lst.append(node_value)
                    else:
                        for val in node_value:
                            lst.append(val)
                elif embedding_type == TupleTokenizationMode.Both_Separated:
                    lst.append(node_type)
                    if not tokenize_all and (not tokenize_number or node_type != "N!"):
                        lst.append(node_value)
                    else:
                        for val in node_value:
                            lst.append(val)
                else:
                    lst.append(node)
        else:
            lst.append(node)
        return TupleEncoder.__get_char_value(lst, node_map, node_id, update_map_node)

    @staticmethod
    def __convert_path_elements(path, edge_map, edge_id, update_map_edge):
        converted_value = ""
        for label in path:
            if label in edge_map:
                value = chr(edge_map[label])
            else:
                value = chr(edge_id)
                update_map_edge[label] = edge_id
                edge_map[label] = edge_id
                edge_id += 1
            converted_value += value
        return converted_value, edge_map, edge_id, update_map_edge

    @staticmethod
    def __get_char_value(lst, map_node, last_id, update_map):
        converted_value = ""
        for item in lst:
            if item in map_node:
                value = chr(map_node.get(item))
            else:
                value = chr(last_id)
                update_map[item] = last_id
                map_node[item] = last_id
                last_id += 1
            converted_value += value
        return converted_value, map_node, last_id, update_map

    @staticmethod
    def __get_tuple_elements(tangent_tuple, ignore_full_relative_path=True):
        if ignore_full_relative_path:
            return tangent_tuple.split("\t")[:3]
        return tangent_tuple.split("\t")[:4]


class EncoderManager:
    """
    Classe Singleton para gerenciar o encoder de tuplas, incluindo carregar/salvar mapas e encodar tuplas
    """

    _instance = None

    # Implementação do Singleton
    def __new__(cls, encoder_map_path=None):
        if cls._instance is None:
            cls._instance = super(EncoderManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        slt_encoder_map_path="lib/tangentCFT/touple_encoder/slt_encoder.tsv",
        opt_encoder_map_path="lib/tangentCFT/touple_encoder/opt_encoder.tsv",
    ):
        # Garantir que a inicialização ocorra apenas uma vez
        if self._initialized:
            return

        self.slt_encoder_map_path = slt_encoder_map_path
        self.slt_encoder_map_node = {}
        self.slt_encoder_map_edge = {}
        self.slt_next_node_id = 60000
        self.slt_next_edge_id = 500
        self.load_encoder_map()
        self._initialized = True

    def load_encoder_map(self):
        """Carrega os mapas do encoder do arquivo"""
        file = open(self.slt_encoder_map_path)
        line = file.readline().strip("\n")
        while line:
            parts = line.split("\t")
            encoder_type = parts[0]
            symbol = parts[1]
            value = int(parts[2])
            if encoder_type == "N":
                self.slt_encoder_map_node[symbol] = value
            else:
                self.slt_encoder_map_edge[symbol] = value
            line = file.readline().strip("\n")
        "The id shows the id that should be assigned to the next character to be encoded (a character that is not seen)" "Therefore there is a plus one in the following lines"
        self.slt_next_node_id = max(list(self.slt_encoder_map_node.values())) + 1
        self.slt_next_edge_id = max(list(self.slt_encoder_map_edge.values())) + 1
        file.close()

    def save_encoder_map(self):
        """Salva os mapas de encoder no arquivo"""
        file = open(self.slt_encoder_map_path, "w")
        for item in self.slt_encoder_map_node:
            file.write(
                "N"
                + "\t"
                + str(item)
                + "\t"
                + str(self.slt_encoder_map_node[item])
                + "\n"
            )
        for item in self.slt_encoder_map_edge:
            file.write(
                "E"
                + "\t"
                + str(item)
                + "\t"
                + str(self.slt_encoder_map_edge[item])
                + "\n"
            )
        file.close()

    def encode_tuples(
        self,
        math_tuples,
        embedding_type=TupleTokenizationMode.Both_Separated,
        ignore_full_relative_path=True,
        tokenize_all=False,
        tokenize_number=True,
    ):
        """
        Encodifica as tuplas da fórmula e atualiza o encoder se necessário

        Args:
            math_tuples: Lista de tuplas extraídas de uma fórmula
            embedding_type: Tipo de embeddings a serem usados
            ignore_full_relative_path: Determina se deve ignorar o caminho relativo completo
            tokenize_all: Determina se todos os elementos devem ser tokenizados
            tokenize_number: Determina se os números devem ser tokenizados

        Returns:
            Lista de tuplas encodificadas
        """
        encoded_tuples, update_map_node, update_map_edge, new_node_id, new_edge_id = (
            TupleEncoder.encode_tuples(
                self.slt_encoder_map_node,
                self.slt_encoder_map_edge,
                self.slt_next_node_id,
                self.slt_next_edge_id,
                math_tuples,
                embedding_type,
                ignore_full_relative_path,
                tokenize_all,
                tokenize_number,
            )
        )

        # Atualizar os IDs e mapas
        self.slt_next_node_id = new_node_id
        self.slt_next_edge_id = new_edge_id
        self.slt_encoder_map_node.update(update_map_node)
        self.slt_encoder_map_edge.update(update_map_edge)

        # Se houve atualização, salvar o encoder
        if update_map_node or update_map_edge:
            print("Adicionando novas tuplas ao encoder... =D ")
            self.save_encoder_map()

        return encoded_tuples
