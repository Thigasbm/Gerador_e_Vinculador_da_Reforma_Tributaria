import conexao_fdb as fdb
import integracao

import platform
print(platform.architecture())
    
opcao = input("Iniciar: [y/n]: ")
while opcao != "y" and opcao != "n":
    print("opcao invalida")
    opcao = input("Iniciar [y/n]: ")
ret = fdb.iniciarPrograma(opcao)

if ret == 1:
    integracao.sql()
    
input("Pressione ENTER para fechar...")