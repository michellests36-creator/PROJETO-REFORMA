
col_left, col_right = st.columns(2)
for idx, (_, row) in enumerate(df_filtrado.iterrows()):
    row_id = int(row["id"])
    target = col_left if idx % 2 == 0 else col_right
    badge = row.get("status") or "Pendente - Fornecedor nao contatado"
    bc = badge_class(badge)
    titulo = f"{safe(row.get('fornecedor'))}"

    with target:
        with st.expander(titulo, expanded=False):
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:12px; border-bottom:1px solid #E5E7EB; padding-bottom:10px;">
                <div>
                    <div style="font-size:15px; font-weight:800; color:#111827;">{safe(row.get('fornecedor'))}</div>
                    <div style="font-size:11px; font-weight:700; color:#6B7280; text-transform:uppercase; margin-top:2px;">{safe(row.get('categoria'))}</div>
                    <div style="font-size:11px; color:#6B7280; margin-top:2px;">CNPJ: {safe(row.get('cnpj'))}</div>
                </div>
                <div><span class="badge badge-{bc}">{safe(badge)}</span></div>
            </div>
            """, unsafe_allow_html=True)

            with st.form(key=f"form_{row_id}"):
                c1, c2 = st.columns(2)
                with c1:
                    data_contato_obj = st.date_input(
                        "DATA DO CONTATO",
                        value=parse_date(row.get("data_contato")),
                        format="DD/MM/YYYY",
                        key=f"data_contato_{row_id}",
                    )
                with c2:
                    canal_atual = row.get("canal_contato")
                    canal_contato = st.selectbox(
                        "CANAL",
                        OPCOES_CANAL,
                        index=OPCOES_CANAL.index(canal_atual) if canal_atual in OPCOES_CANAL else 0,
                        key=f"canal_{row_id}",
                    )

                c3, c4 = st.columns(2)
                with c3:
                    rec_opts = ["Pendente", "Sim", "Nao"]
                    rec_atual = str(row.get("recebeu") or "Pendente").replace("Não", "Nao")
                    recebeu = st.selectbox(
                        "RECEBEU COMUNICADO?",
                        rec_opts,
                        index=rec_opts.index(rec_atual) if rec_atual in rec_opts else 0,
                        key=f"rec_{row_id}",
                    )
                with c4:
                    reen_opts = ["Nao", "Sim"]
                    reen_atual = str(row.get("reenvio_necessario") or "Nao").replace("Não", "Nao")
                    reenvio = st.selectbox(
                        "REENVIO NECESSARIO?",
                        reen_opts,
                        index=reen_opts.index(reen_atual) if reen_atual in reen_opts else 0,
                        key=f"reenvio_{row_id}",
                    )

                chk1 = st.checkbox("Ja acompanha Reforma?", value=parse_bool(row.get("acompanha_reforma")), key=f"chk1_{row_id}")
                chk2 = st.checkbox("Ja discutiu internamente?", value=parse_bool(row.get("discutiu_internamente")), key=f"chk2_{row_id}")
                chk3 = st.checkbox("Ja falou c/ contador?", value=parse_bool(row.get("falou_contador")), key=f"chk3_{row_id}")

                c5, c6 = st.columns(2)
                with c5:
                    resp_cont = st.text_input(
                        "RESPONSAVEL INTERNO / CONTADOR",
                        value=str(row.get("responsavel_contador") or ""),
                        placeholder="Ex: Joao - Contador",
                        key=f"resp_{row_id}",
                    )
                with c6:
                    opcoes_2027 = [
                        "Em analise",
                        "Manter Simples Nacional",
                        "Migrar para Simples Hibrido",
                        "Migrar para Lucro Presumido",
                        "Migrar para Lucro Real",
                        "Aguardando orientacao contabil",
                        "Ainda sem definicao",
                        "Nao informado",
                    ]
                    def_atual = str(row.get("definicao_2027") or "").replace("análise", "analise")
                    def_2027 = st.selectbox(
                        "DEFINICAO PRELIMINAR 2027",
                        opcoes_2027,
                        index=opcoes_2027.index(def_atual) if def_atual in opcoes_2027 else 0,
                        key=f"def_{row_id}",
                    )

                c7, c8 = st.columns(2)
                with c7:
                    prev_obj = st.date_input(
                        "PREVISAO RETORNO",
                        value=parse_date(row.get("previsao_retorno")),
                        format="DD/MM/YYYY",
                        key=f"prev_{row_id}",
                    )
                with c8:
                    prox_contato_obj = st.date_input(
                        "DATA PROXIMO CONTATO",
                        value=parse_date(row.get("data_proximo_contato")),
                        format="DD/MM/YYYY",
                        key=f"prox_contato_{row_id}",
                    )

                c9, c10 = st.columns(2)
                with c9:
                    status = st.selectbox(
                        "STATUS OFICIAL",
                        STATUS_OPTIONS,
                        index=status_option_index(row.get("status")),
                        key=f"stat_{row_id}",
                    )
                with c10:
                    valor_acao_atual = row.get("proxima_acao")
                    prox_acao = st.selectbox(
                        "PROXIMA ACAO",
                        OPCOES_PROXIMA_ACAO,
                        index=OPCOES_PROXIMA_ACAO.index(valor_acao_atual) if valor_acao_atual in OPCOES_PROXIMA_ACAO else 0,
                        key=f"acao_{row_id}",
                    )

                obs = st.text_area(
                    "OBSERVACAO + EVIDENCIAS",
                    value=str(row.get("observacao") or ""),
                    key=f"obs_{row_id}",
                    height=90,
                )

                submitted = st.form_submit_button("SALVAR", use_container_width=True)

                if submitted:
                    payload = {
                        "data_contato": format_date(data_contato_obj),
                        "canal_contato": canal_contato,
                        "recebeu": recebeu,
                        "reenvio_necessario": reenvio,
                        "acompanha_reforma": bool(chk1),
                        "discutiu_internamente": bool(chk2),
                        "falou_contador": bool(chk3),
                        "responsavel_contador": resp_cont,
                        "definicao_2027": def_2027,
                        "previsao_retorno": format_date(prev_obj),
                        "data_proximo_contato": format_date(prox_contato_obj),
                        "status": status,
                        "proxima_acao": prox_acao,
                        "observacao": obs,
                    }
                    try:
                        salvar_tratativa(row_id, payload, st.session_state.usuario_logado)
                        carregar_contatos.clear()
                        st.success("Salvo com sucesso no Supabase.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar. Nada foi confirmado no banco: {e}")
