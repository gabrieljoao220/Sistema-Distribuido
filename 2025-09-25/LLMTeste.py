import pandas as pd
import random
import itertools
import re

# ==============================================================================
# 1. FILTRO DE SEGURANÇA
# Adicionamos uma lista de palavras que não devem aparecer nos exemplos.
# A geração atual não produz essas palavras, mas é uma camada extra de segurança.
# Você pode adicionar qualquer palavra que julgar inadequada a esta lista.
# ==============================================================================
PALAVRAS_FILTRADAS = [
    # Adicione aqui palavras de baixo calão ou inadequadas em português
    # Exemplo:
    "palavrao1", "palavrao2", "qualqueroutrapalavra"
]

def contem_palavra_impropria(texto):
    """Verifica se o texto contém alguma palavra da lista de filtragem."""
    # Cria uma expressão regular que encontra palavras inteiras, ignorando maiúsculas/minúsculas
    # O \b garante que estamos pegando a palavra inteira (ex: 'mar' e não 'amar')
    for palavra in PALAVRAS_FILTRADAS:
        if re.search(r'\b' + re.escape(palavra) + r'\b', texto, re.IGNORECASE):
            return True
    return False

# ==============================================================================
# 2. BLOCOS DE CONSTRUÇÃO (COMPONENTES)
# Listas seguras e apropriadas para o público-alvo.
# ==============================================================================

sujeitos_crianca = ["Eu", "A gente", "Eu e meu amigo(a)", "Nós"]
sujeitos_outros = ["O(A) {nome}", "Meu colega", "A professora", "O papai", "A mamãe"]

verbos_rotina = ["preciso", "tenho que", "vou", "quero", "esqueci de"]
acoes_rotina = ["arrumar a cama", "escovar os dentes", "guardar os brinquedos", "fazer a lição", "tomar banho", "colocar o pijama", "lavar as mãos", "comer a fruta"]

verbos_sociais = ["brincar com", "conversar com", "dividir o lanche com", "pedir ajuda para", "dizer obrigado para", "emprestar o brinquedo para"]
nomes = ["Ana", "Bruno", "Carla", "Davi", "Elisa", "Fábio", "Gabi", "Hugo", "Isis", "João", "Lara", "Miguel"]

verbos_emocionais = ["estou me sentindo", "fiquei", "acho que estou", "me senti um pouco"]
emocoes = ["feliz", "triste", "bravo(a)", "animado(a)", "frustrado(a)", "com medo", "confuso(a)", "orgulhoso(a)"]
causas_emocoes = ["porque ganhei no jogo", "porque não consegui desenhar", "porque meu amigo me ajudou", "porque vou ao parque hoje", "porque o dia está chuvoso", "porque aprendi algo novo"]

verbos_aprendizado = ["o que é", "como se faz", "me explica de novo", "qual a cor do(a)", "que som faz o(a)"]
conceitos = ["círculo", "quadrado", "amizade", "paciência", "sol", "lua", "cachorro", "gato", "leão", "árvore", "flor"]

# Respostas Padrão
respostas_incentivo = ["Que bom que você perguntou! Vamos descobrir juntos.", "Ótima pergunta! Isso mostra que você está pensando.", "Claro! Estou aqui para te ajudar a aprender."]
respostas_apoio_emocional = ["É normal se sentir assim. Quer conversar sobre isso?", "Obrigado por me contar como você se sente. Vamos respirar fundo.", "Eu entendo. Esse sentimento passa. Que tal fazermos algo que você gosta?"]
respostas_guia_social = ["Isso é muito legal da sua parte!", "Tentar ser amigo é sempre uma boa ideia.", "Essa é uma ótima maneira de fazer amigos."]
respostas_rotina_positiva = ["Isso é muito importante para ficarmos saudáveis e organizados!", "Excelente! Manter a rotina nos ajuda a ter um dia ótimo.", "Vamos fazer isso! Depois você vai se sentir muito bem."]

# ==============================================================================
# 3. MOTOR DE GERAÇÃO MASSIVA E FILTRADA
# ==============================================================================

def gerar_dataset(total_exemplos):
    dataset = set()

    print(f"Iniciando a geração massiva de {total_exemplos} exemplos filtrados...")

    # Loop para garantir que atinjamos o número desejado de exemplos únicos e seguros
    while len(dataset) < total_exemplos:

        molde = random.randint(1, 4)

        instrucao, entrada, saida = "", "", ""

        if molde == 1: # Rotina
            instrucao = "Oriente sobre uma tarefa de rotina."
            entrada = f"{random.choice(sujeitos_crianca)} {random.choice(verbos_rotina)} {random.choice(acoes_rotina)}."
            saida = random.choice(respostas_rotina_positiva)

        elif molde == 2: # Social
            instrucao = "Incentive uma interação social positiva."
            nome_sujeito = random.choice(nomes)
            sujeito = random.choice(sujeitos_outros).format(nome=nome_sujeito)
            entrada = f"{sujeito} não quer {random.choice(verbos_sociais).split(' com')[0]} comigo."
            saida = f"Às vezes as pessoas não querem brincar, e tudo bem. Que tal procurar outro amigo ou brincar de outra coisa?"

        elif molde == 3: # Emocional
            instrucao = "Valide um sentimento e ofereça apoio."
            entrada = f"Eu {random.choice(verbos_emocionais)} {random.choice(emocoes)} porque {random.choice(causas_emocoes)}."
            saida = random.choice(respostas_apoio_emocional)

        elif molde == 4: # Aprendizado
            instrucao = "Responda a uma pergunta de conhecimento."
            entrada = f"{random.choice(verbos_aprendizado)} {random.choice(conceitos)}?"
            saida = random.choice(respostas_incentivo)

        # APLICAÇÃO DO FILTRO DE SEGURANÇA
        if not contem_palavra_impropria(entrada) and not contem_palavra_impropria(saida):
            dataset.add((instrucao, entrada, saida))

        # Mostra o progresso a cada 1000 novos exemplos gerados
        if len(dataset) % 1000 == 0 and len(dataset) > 0:
            # Esta linha evita prints repetidos para o mesmo marco
            current_progress = len(dataset)
            if 'last_progress' not in locals() or last_progress != current_progress:
                print(f"Progresso: {current_progress} de {total_exemplos} exemplos únicos e seguros...")
                last_progress = current_progress

    print(f"Geração concluída! Total de {len(dataset)} exemplos únicos e seguros.")
    return list(dataset)

# ==============================================================================
# 4. EXECUÇÃO
# ==============================================================================

# AQUI ESTÁ A META ATUALIZADA
TOTAL_DE_EXEMPLOS = 25000

meu_dataset = gerar_dataset(TOTAL_DE_EXEMPLOS)

# Pega o número exato de exemplos solicitados
final_dataset_list = meu_dataset[:TOTAL_DE_EXEMPLOS]

df = pd.DataFrame(final_dataset_list, columns=['Instrução', 'Entrada', 'Saída Esperada'])
df = df.sample(frac=1).reset_index(drop=True)

# Novo nome de arquivo para refletir a quantidade e o filtro
df.to_csv('dataset_25k_filtrado.csv', index=False, sep='|', encoding='utf-8-sig')

print(f"\nArquivo 'dataset_25k_filtrado.csv' salvo com sucesso!")
print("\n--- 10 Primeiros Exemplos do Dataset Final ---")
print(df.head(10))