import conexao_fdb as fdb
import planilha
import time


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
        CST_IBSCBS,
        CCLASSTRIB_IBSCBS,
        PERC_RED_IBSMUN,
        PERC_RED_CBS,
        PERC_RED_IBSUF,
        PERC_DIF_IBSMUN,
        PERC_DIF_CBS,
        PERC_DIF_IBSUF,
        ALIQ_IBS_MONO,
        ALIQ_CBS_MONO,
        FATOR_QTDBC_MONO
        FROM TRIBUTACAO
        """)
    
    tributacoes = {}
    
    for row in cur.fetchall():
        (
            id_,
            cst,
            cclasstrib,
            redIbsMun,
            redCbs,
            redIbsUf,
            difIbsMun,
            difCbs,
            difIbsUf,
            aliqMonIbs,
            aliqMonCbs,
            fatorQtdBcMon
        ) = row

        chave = (
            str(cst).strip(),
            str(cclasstrib).strip(),
            float(redIbsMun),
            float(redCbs),
            float(redIbsUf),
            float(difIbsMun),
            float(difCbs),
            float(difIbsUf),
            float(aliqMonIbs),
            float(aliqMonCbs),
            float(fatorQtdBcMon)
        )

        tributacoes[chave] = id_
    
    
    print(f"Produtos encontrados: {total}")

    # PROCESSAMENTO
    for i, (codigo, cod_ncm) in enumerate(produtos, start=1):
        cod_ncm = str(cod_ncm).strip()
        
        # bloqueio para exec de amostra
        if i >= 10:
            break;

        if cod_ncm not in planilha.dados_planilha:
            continue

        dados = planilha.dados_planilha[cod_ncm]

        cst = str(dados["cst"]).strip()
        cclasstrib = str(dados["cClassTrib"]).strip()
        
        redIbsMun = float(dados["redIBSMUN"] or 0)
        redCbs = float(dados["redCBS"] or 0)
        redIbsUf = float(dados["redIBSUF"] or 0)
        
        difIbsMun = float(dados["difIBSMUN"] or 0)
        difCbs = float(dados["difCBS"] or 0)
        difIbsUf = float(dados["difIBSUF"] or 0)
        
        aliqMonIbs = float(dados["aliqMonIBS"] or 0)
        aliqMonCbs = float(dados["aliqMonCBS"] or 0)
        fatorQtdBcMon = float(dados["fatorQtdBCMon"] or 0)

        # pega IDs sem consultar banco
        id_cst_ibscbs = csts.get(cst)
        id_classificacao_tributaria = classificacoes.get(cclasstrib)

        if id_cst_ibscbs is None:
            print(f"CST não encontrado: {cst}")
            continue

        if id_classificacao_tributaria is None:
            print(f"Classificação não encontrada: {cclasstrib}")
            continue

        chave = (
            cst,
            cclasstrib,
            
            redIbsMun,
            redCbs,
            redIbsUf,
            
            difIbsMun,
            difCbs,
            difIbsUf,
            
            aliqMonIbs,
            aliqMonCbs,
            fatorQtdBcMon
        )
    
        # BUSCA TRIBUTAÇÃO NO CACHE
        if chave in tributacoes:
            id_tributacao = tributacoes[chave]
        else:
            # cria tributação
            cur.execute("""
                INSERT INTO TRIBUTACAO
                (
                    DESCRICAO,
                    CST_IBSCBS,
                    CCLASSTRIB_IBSCBS,

                    PERC_DIF_IBSUF,
                    PERC_RED_IBSUF,

                    PERC_DIF_IBSMUN,
                    PERC_RED_IBSMUN,

                    PERC_DIF_CBS,
                    PERC_RED_CBS,

                    FATOR_QTDBC_MONO,

                    ALIQ_IBS_MONO,
                    ALIQ_CBS_MONO,

                    APLICA_IS,

                    CST_IS,
                    CCLASSTRIB_IS,

                    ALIQ_IS,

                    REG_CST_IBSCBS,
                    REG_CCLASSTRIB_IBSCBS,

                    ID_CST_IBSCBS,
                    ID_CLASSIFICACAO_TRIBUTARIA
                )
                VALUES
                (
                    ?,
                    ?,
                    ?,

                    ?,
                    ?,

                    ?,
                    ?,

                    ?,
                    ?,

                    ?,

                    ?,
                    ?,

                    1,

                    '',
                    '',

                    0,

                    '',
                    '',

                    ?,
                    ?
                )
                RETURNING ID
            """,
            (
                f"{cst} - {cclasstrib}",
                cst,
                cclasstrib,

                difIbsUf,
                redIbsUf,

                difIbsMun,
                redIbsMun,

                difCbs,
                redCbs,

                fatorQtdBcMon,

                aliqMonIbs,
                aliqMonCbs,

                id_cst_ibscbs,
                id_classificacao_tributaria
            ))

            id_tributacao = cur.fetchone()[0]
            
            tributacoes[chave] = id_tributacao

        # UPDATE PRODUTO
        cur.execute("UPDATE ESTOQUE SET ID_TRIBUTACAO = ? WHERE CODIGO = ? ", (id_tributacao, codigo))

        # LOG DE PROGRESSO
        if i % 500 == 0:
            decorrido = int(time.time() - inicio)
            restante = int(
                (total - i) *
                (decorrido / i)
            )
            print(
                f"[{i}/{total}] "
                f"Tempo: {decorrido//60:02d}:{decorrido%60:02d} "
                f"| Restante: {restante//60:02d}:{restante%60:02d}"
            )

    # COMMIT ÚNICO
    con.commit()
    
    fim = time.time()
    print("=" * 50)
    print("Processamento concluído")
    print(f"Produtos analisados: {total}")
    print(
        f"Tempo total: {(fim-inicio)/60:.2f} minutos"
    )
    print(
        f"Tributações em cache: {len(tributacoes)}"
    )
    print("=" * 50)