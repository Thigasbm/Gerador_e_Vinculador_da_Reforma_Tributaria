import conexao_fdb as fdb
import planilha
import time
from decimal import Decimal


def sql():
    con = fdb.conectar_fb5(
        fdb.caminho,
        fdb.usuario,
        fdb.senha
    )

    cur = con.cursor()

    inicio = time.time()

    # CARREGA PRODUTOS
    cur.execute("SELECT CODIGO, COD_NCM FROM ESTOQUE")
    produtos = cur.fetchall()
    total = len(produtos)

    # CARREGA CST EM MEMÓRIA
    cur.execute("SELECT ID, CODIGO FROM CST_IBSCBS")
    csts = {
        str(codigo).strip(): id_
        for id_, codigo in cur.fetchall()
    }

    # CARREGA CLASSIFICAÇÃO
    cur.execute("SELECT ID, CODIGO FROM CLASSIFICACAO_TRIBUTARIA")
    classificacoes = {
        str(codigo).strip(): id_
        for id_, codigo in cur.fetchall()
    }

    # CACHE TRIBUTAÇÕES
    cur.execute("""
        SELECT
        ID,
        DESCRICAO,
        CST_IBSCBS,
        CCLASSTRIB_IBSCBS
        FROM TRIBUTACAO
        """)
    
    tributacoes = {}
    
    for id_, descricao, cst, cclasstrib in cur.fetchall():
        cst_str = str(cst).strip()
        cclasstrib_str = str(cclasstrib).strip()
        desc_str = str(descricao).strip()
        
        if cst_str == "000":
            chave = (cst_str, cclasstrib_str)
            print(f"Cache CST 000 carregado: {chave}")
        else:
            desc_partes = desc_str.split(" - ")
            # Só assume que é NCM se a descrição foi salva no formato padrão de 3 partes
            if len(desc_partes) >= 3:
                ncm_desc = desc_partes[-1].strip()
            else:
                ncm_desc = "" # Registro antigo fora do padrão, força criar o certo
            
            chave = (cst_str, cclasstrib_str, ncm_desc)
            print(f"Cache Outros CSTs carregado: {chave}")

        tributacoes[chave] = id_
    
    print(f"\nProdutos encontrados no ESTOQUE: {total}")

    # PROCESSAMENTO
    for i, (codigo, cod_ncm) in enumerate(produtos, start=1):
        cod_ncm = str(cod_ncm).strip()

        if cod_ncm not in planilha.dados_planilha:
            # Remova ou comente este print se tiver muitos produtos sem NCM na planilha
            print(f"Produto {codigo} pulado: NCM {cod_ncm} não está na planilha.")
            continue

        dados = planilha.dados_planilha[cod_ncm]

        cst = str(dados["cst"]).strip()
        cclasstrib = str(dados["cClassTrib"]).strip()

        # pega IDs sem consultar banco
        id_cst_ibscbs = csts.get(cst)
        id_classificacao_tributaria = classificacoes.get(cclasstrib)

        if id_cst_ibscbs is None:
            print(f"Produto {codigo} pulado: CST {cst} não cadastrado no banco (CST_IBSCBS).")
            continue

        if id_classificacao_tributaria is None:
            print(f"Produto {codigo} pulado: Classificação {cclasstrib} não cadastrada no banco (CLASSIFICACAO_TRIBUTARIA).")
            continue
        
        # Regra de chaves
        if cst == "000":
            chave = (cst, cclasstrib)
            descricao = f"{cst} - {cclasstrib}"
        else:
            chave = (cst, cclasstrib, cod_ncm)
            descricao = f"{cst} - {cclasstrib} - {cod_ncm}"
            
        # BUSCA TRIBUTAÇÃO NO CACHE
        if chave in tributacoes:
            id_tributacao = tributacoes[chave]
        else:
            # cria tributação
            cur.execute("""
                INSERT INTO TRIBUTACAO
                (
                    DESCRICAO, CST_IBSCBS, CCLASSTRIB_IBSCBS,
                    PERC_DIF_IBSUF, PERC_RED_IBSUF,
                    PERC_DIF_IBSMUN, PERC_RED_IBSMUN,
                    PERC_DIF_CBS, PERC_RED_CBS,
                    FATOR_QTDBC_MONO, ALIQ_IBS_MONO, ALIQ_CBS_MONO,
                    APLICA_IS, CST_IS, CCLASSTRIB_IS, ALIQ_IS,
                    REG_CST_IBSCBS, REG_CCLASSTRIB_IBSCBS,
                    ID_CST_IBSCBS, ID_CLASSIFICACAO_TRIBUTARIA
                )
                VALUES
                (
                    ?, ?, ?,
                    0, 0, 0, 0, 0, 0, 0, 0, 0,
                    1, '', '', 0, '', '',
                    ?, ?
                )
                RETURNING ID
            """,
            (
                descricao, cst, cclasstrib,
                id_cst_ibscbs, id_classificacao_tributaria
            ))

            id_tributacao = cur.fetchone()[0]
            tributacoes[chave] = id_tributacao
            print(f"!!! Nova tributação criada: {descricao} (ID: {id_tributacao})")

        # UPDATE PRODUTO
        cur.execute("UPDATE ESTOQUE SET ID_TRIBUTACAO = ? WHERE CODIGO = ? ", (id_tributacao, codigo))

        # LOG DE PROGRESSO
        if i % 500 == 0:
            decorrido = int(time.time() - inicio)
            restante = int((total - i) * (decorrido / i))
            print(
                f"[{i}/{total}] "
                f"Tempo: {decorrido//60:02d}:{decorrido%60:02d} "
                f"| Restante: {restante//60:02d}:{restante%60:02d}"
            )

    # COMMIT ÚNICO
    con.commit()
    cur.close()
    con.close()
    
    fim = time.time()
    print("=" * 50)
    print("Processamento concluído")
    print(f"Produtos analisados: {total}")
    print(f"Tempo total: {(fim-inicio)/60:.2f} minutos")
    print(f"Tributações em cache: {len(tributacoes)}")
    print("=" * 50)