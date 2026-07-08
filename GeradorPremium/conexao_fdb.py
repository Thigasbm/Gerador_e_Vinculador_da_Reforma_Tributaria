from firebird.driver import connect

caminho = r"C:\GDOOR Sistemas\GDOOR PRO\DATAGES.FDB"
usuario = "SYSDBA"
senha = "masterkey"

def conectar_fb5(caminho, usuario, senha):
    
    return connect(
        database=caminho,
        user=usuario,
        password=senha
    )

def iniciarPrograma(opcao):
    if opcao == "y":
        try:
            conectar_fb5(
                caminho,
                usuario,
                senha
            )

            print("FDB Conectado com sucesso!")
            return 1
        except Exception as e:
            import traceback
            traceback.print_exc(e)        
        
    elif opcao=="n":
        print("Finalizando programa...")
        return 0
    