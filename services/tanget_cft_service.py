import logging
import os
import numpy
from Configuration.configuration import Configuration
from lib.tangentCFT.model import TangentCftModel
from torch.autograd import Variable
import torch
import torch.nn.functional as F
from lib.tangentCFT.touple_encoder.encoder import EncoderManager
from typing import Literal

# Remover ou comentar esta linha
# os.environ['CUDA_VISIBLE_DEVICES'] = '0'
# Remover ou comentar esta linha
# use_cuda = torch.cuda.is_available()


class TangentCFTService:
    def __init__(
        self,
        model_file_path=None,
    ):
        """
        Inicializa o serviço TangentCFT com modelo e encoder
        """
        self.model = TangentCftModel()
        if model_file_path is not None:
            print("Loading the model")
            self.model.load_model(model_file_path)

        # Usar o singleton EncoderManager
        self.encoder_manager = EncoderManager()

    def train_model(self, configuration, lst_lst_encoded_tuples):
        print("Setting Configuration")
        self.model.train(configuration, lst_lst_encoded_tuples)
        return self.model

    def save_model(self, model_file_path):
        self.model.save_model(model_file_path)

    def index_collection_to_tensors(self, dictionary_formula_lst_encoded_tuples):
        """
        Get dictionary of formula ids and their list of tuples and return matrix of tensors and a
        dictionary having formula id and their corresponding row id in the matrix
        """
        numpy_lst = []
        index_formula_id = {}
        idx = 0
        for formula in dictionary_formula_lst_encoded_tuples:
            try:
                xx = self.__get_vector_representation(
                    dictionary_formula_lst_encoded_tuples[formula]
                )
                xx = xx.reshape(1, 300)
                numpy_lst.append(xx)
                index_formula_id[idx] = formula
                idx += 1
            except:
                continue
        temp = numpy.concatenate(numpy_lst, axis=0)
        # Remover .cuda()
        tensor_values = Variable(torch.tensor(temp).double())
        return tensor_values, index_formula_id

    def index_collection_to_numpy(self, dictionary_formula_lst_encoded_tuples):
        """
        This methods takes in the dictionary of formula id and their corresponding list of tuples and returns a dictionary
        of formula id and their numpy vector representations
        """
        index_formula_id = {}
        for formula in dictionary_formula_lst_encoded_tuples:
            vector = self.__get_vector_representation(
                dictionary_formula_lst_encoded_tuples[formula]
            )
            vector = vector.reshape(1, 300)
            index_formula_id[formula] = vector
        return index_formula_id

    def get_query_vector(self, lst_encoded_tuples):
        return self.__get_vector_representation(lst_encoded_tuples)

    def encode_formula_tuples(
        self,
        formula_tuples,
        encoder_type: Literal["SLT", "OPT", "SLT_TYPE"],
        embedding_type=None,
        tokenize_numbers=None,
    ):
        """
        Encodifica as tuplas da fórmula usando o EncoderManager

        Args:
            formula_tuples: Lista de tuplas extraídas de uma fórmula

        Returns:
            Lista de tuplas encodificadas
        """
        # Apenas passa os parâmetros que não são None
        kwargs = {}
        if embedding_type is not None:
            kwargs["embedding_type"] = embedding_type
        if tokenize_numbers is not None:
            kwargs["tokenize_numbers"] = tokenize_numbers
        kwargs["encoder_type"] = encoder_type
        return self.encoder_manager.encode_tuples(formula_tuples, **kwargs)

    @staticmethod
    def formula_retrieval(collection_tensor, formula_index, query_vector, top_k=10):
        """
        Parameters:
            collection_tensor: matric of tensor, each row vector representation of formula in the collection
            formula_index: dictionary mapping each row of tensor matrix to a formula id
            query_vector: formula query vector representation in numpy
            top_k: número de resultados a retornar (default 10)
        """
        query_vector = query_vector.reshape(1, 300)
        # Remover .cuda()
        query_vec = Variable(torch.tensor(query_vector).double())
        dist = F.cosine_similarity(collection_tensor, query_vec)
        index_sorted = torch.sort(dist, descending=True)[1]
        # Usar top_k ao invés de 1000
        top_k_indices = index_sorted[:top_k]
        # Remover .cpu()
        top_k_indices = top_k_indices.data.numpy()
        cos_values = torch.sort(dist, descending=True)[0][:top_k].data.numpy()
        result = {}
        count = 1
        for x in top_k_indices:
            doc_id = formula_index[x]
            score = cos_values[count - 1]
            result[doc_id] = score
            count += 1
        return result

    def __get_vector_representation(self, lst_encoded_tuples):
        """
         This method take the converted-tuple formula file path (the file on which a list the converted tuples for
         formula is saved, then it get vector representation of each of the tuple. The formula vector is the average of its
         tuples vectors.
        :param lst_encoded_tuples: averaging vector representation for these tuples
        :return: vector representation for the formula
        """
        temp_vector = None
        first = True
        counter = 0
        for encoded_tuple in lst_encoded_tuples:
            # if the tuple vector cannot be extracted due to unseen n-gram, then we pass over that tuple.
            try:
                if first:
                    temp_vector = self.model.get_vector_representation(encoded_tuple)
                    first = False
                else:
                    temp_vector = temp_vector + self.model.get_vector_representation(
                        encoded_tuple
                    )
                counter = counter + 1
            except Exception as e:
                logging.exception(e)
        return temp_vector / counter
