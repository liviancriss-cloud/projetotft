"""Interface web do EditalClaro (Gradio): chat com o edital e painel de prazos.

Uso:
    python app.py
"""

import gradio as gr

from src.busca import indice_disponivel, info_edital
from src.config import EXPORTS_DIR, PORT
from src.prazos import extrair_prazos, formatar_periodo, gerar_ics
from src.resposta import responder

AVISO = (
    "⚠️ **Projeto educacional.** As respostas são geradas por IA a partir do edital carregado. "
    "Sempre confirme datas e regras no edital oficial."
)

EXEMPLOS = [
    "Qual o prazo final para pagar a taxa de inscrição?",
    "Quais documentos preciso enviar na matrícula?",
    "Existe reserva de vagas? Quem pode concorrer?",
    "Quando sai o resultado preliminar e até quando posso recorrer?",
]


def texto_status() -> str:
    if not indice_disponivel():
        return (
            "❌ Nenhum edital processado. Rode `python src/ingestao.py data/editais/seu_edital.pdf` "
            "e reinicie o app."
        )
    info = info_edital() or {}
    return (
        f"📄 Edital carregado: **{info.get('arquivo', '?')}** "
        f"({info.get('paginas', '?')} páginas, {info.get('trechos', '?')} trechos)"
    )


def enviar_pergunta(mensagem: str, historico: list[dict] | None):
    historico = list(historico or [])
    if not mensagem or not mensagem.strip():
        return "", historico

    historico.append({"role": "user", "content": mensagem})
    try:
        texto = responder(mensagem).formatar()
    except (FileNotFoundError, ValueError) as erro:
        texto = f"⚠️ {erro}"
    except Exception as erro:  # noqa: BLE001 - mostra o problema em vez de quebrar a interface
        texto = f"⚠️ Não consegui responder agora ({type(erro).__name__}). Tente novamente em instantes."
        print(f"[erro] {type(erro).__name__}: {erro}")
    historico.append({"role": "assistant", "content": texto})
    return "", historico


def atualizar_prazos(forcar: bool):
    try:
        prazos = extrair_prazos(forcar=forcar)
    except Exception as erro:  # noqa: BLE001
        print(f"[erro] {type(erro).__name__}: {erro}")
        return [], None, f"⚠️ Não foi possível extrair os prazos: {erro}"

    if not prazos:
        return [], None, "Nenhum prazo encontrado neste edital."

    linhas = [[p.evento, formatar_periodo(p), p.pagina, p.trecho] for p in prazos]
    caminho = gerar_ics(prazos)
    return (
        linhas,
        str(caminho),
        f"✅ {len(prazos)} prazos encontrados. Confira cada um na página indicada do edital.",
    )


with gr.Blocks(title="EditalClaro") as demo:
    gr.Markdown("# 📑 EditalClaro\nTire dúvidas sobre o edital e acompanhe os prazos.")
    gr.Markdown(texto_status())

    with gr.Tab("💬 Perguntas"):
        chat = gr.Chatbot(type="messages", height=460, label="Conversa")
        caixa = gr.Textbox(
            placeholder="Pergunte algo sobre o edital e pressione Enter...", show_label=False
        )
        gr.Examples(examples=EXEMPLOS, inputs=caixa, label="Exemplos de perguntas")
        gr.Button("🧹 Limpar conversa").click(lambda: [], None, chat)
        caixa.submit(enviar_pergunta, [caixa, chat], [caixa, chat])

    with gr.Tab("📅 Prazos"):
        gr.Markdown("Extrai do edital as datas de inscrição, provas, resultados e recursos.")
        with gr.Row():
            botao = gr.Button("Extrair prazos", variant="primary")
            botao_refazer = gr.Button("Refazer extração")
        situacao = gr.Markdown()
        tabela = gr.Dataframe(
            headers=["Evento", "Data", "Página", "Trecho do edital"],
            interactive=False,
            wrap=True,
        )
        arquivo_ics = gr.File(label="Calendário (.ics)", interactive=False)

        botao.click(lambda: atualizar_prazos(False), None, [tabela, arquivo_ics, situacao])
        botao_refazer.click(lambda: atualizar_prazos(True), None, [tabela, arquivo_ics, situacao])

    gr.Markdown(AVISO)


if __name__ == "__main__":
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    demo.launch(server_name="0.0.0.0", server_port=PORT, allowed_paths=[str(EXPORTS_DIR)])
