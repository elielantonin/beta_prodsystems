import sqlite3
import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

# Função para criar as tabelas necessárias
def criar_tabelas():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Criar tabela de alunos
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS alunos (
            matricula INTEGER PRIMARY KEY AUTOINCREMENT,
            unidade TEXT NOT NULL,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            data_nascimento DATE,
            endereco TEXT,
            telefone TEXT,
            email TEXT
        )
    ''')

    # Criar tabela de pagamentos
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS pagamentos (
            codigo_pagamento INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula INTEGER,
            unidade TEXT NOT NULL,
            nome TEXT,
            cpf TEXT,
            data_pagamento DATE,
            plano TEXT,
            valor REAL,
            FOREIGN KEY (matricula) REFERENCES alunos (matricula)
        )
    ''')

    conn.commit()
    conn.close()

# Função para buscar aluno
def buscar_aluno(busca_por, valor):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    if busca_por == "Matrícula":
        c.execute("SELECT * FROM alunos WHERE matricula = ?", (valor,))
    elif busca_por == "Nome":
        c.execute("SELECT * FROM alunos WHERE nome LIKE ?", ('%' + valor + '%',))
    elif busca_por == "CPF":
        c.execute("SELECT * FROM alunos WHERE cpf = ?", (valor,))
    
    aluno = c.fetchone()
    conn.close()
    return aluno

# Função para registrar pagamento
def registrar_pagamento(matricula, unidade, nome, cpf, data_pagamento, plano, valor):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        data_pagamento_str = data_pagamento.strftime('%Y-%m-%d')
        c.execute(''' 
            INSERT INTO pagamentos (matricula, unidade, nome, cpf, data_pagamento, plano, valor) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (matricula, unidade, nome, cpf, data_pagamento_str, plano, valor))
        
        conn.commit()
        codigo_pagamento = c.lastrowid  # Obtém o código de pagamento auto-incrementado
        st.write(f"Dados inseridos: {codigo_pagamento}, {matricula}, {unidade}, {nome}, {cpf}, {data_pagamento}, {plano}, {valor}")
    except sqlite3.Error as e:
        st.write(f"Erro ao registrar pagamento: {e}")
        return None
    finally:
        conn.close()
        
    return codigo_pagamento

# Função para limpar os campos após registrar o pagamento
def limpar_campos():
    st.session_state.aluno_encontrado = None
    st.session_state.valor_mensalidade = 0.0

# Função para calcular o status do próximo pagamento com base no plano
def alerta_proximo_pagamento(data_pagamento, plano):
    if isinstance(data_pagamento, str):
        data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d %H:%M:%S')

    periodicidade_meses = {
        'mensal': 1,
        'trimestral': 3,
        'semestral': 6,
        'anual': 12
    }

    plano = plano.lower()
    if plano not in periodicidade_meses:
        return None

    proximo_pagamento = data_pagamento + relativedelta(months=periodicidade_meses[plano])
    hoje = datetime.now().date()
    return "Atrasado" if proximo_pagamento.date() < hoje else "Em dia"

# Interface do Streamlit
st.title("\U0001F4B3 Pagamento")

# Criar tabelas se não existirem
criar_tabelas()

# Definir as abas
tab1, tab2, tab3 = st.tabs(["\U0001F4C1 Dados Gerais", "\U0001F4C1 Inserir", "\U0001F4C1 Editar/Excluir"])

# Aba de dados gerais
with tab1:
    
    conn = sqlite3.connect('database.db')
    try:
        query = "SELECT nome, plano, data_pagamento FROM pagamentos"
        dados = pd.read_sql_query(query, conn)
        dados['data_pagamento'] = pd.to_datetime(dados['data_pagamento'], format='%Y-%m-%d', errors='coerce')
        dados['Status'] = dados.apply(lambda row: alerta_proximo_pagamento(row['data_pagamento'], row['plano']), axis=1)

        st.title("Painel de Pagamentos de Alunos")
        st.write("Visualize o status das mensalidades dos alunos com base no plano e último pagamento registrado.")

        filtro_status = st.selectbox("Filtrar por status", ["Todos", "Atrasado", "Pagamento próximo!", "Em dia"])
        if filtro_status != "Todos":
            dados = dados[dados["Status"] == filtro_status]

        st.dataframe(dados[['nome', 'plano', 'Status']])

    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {str(e)}")
    finally:
        conn.close()

# Aba de inserção de dados
with tab2:
    busca_por = st.selectbox("Buscar por", ["Matrícula", "Nome", "CPF"])
    valor_busca = st.text_input("Insira o valor para buscar")

    if "aluno_encontrado" not in st.session_state:
        st.session_state.aluno_encontrado = None
    
    if st.button("\U0001F50D Buscar"):
        if valor_busca:
            aluno = buscar_aluno(busca_por, valor_busca)
            if aluno:
                st.session_state.aluno_encontrado = aluno
                matricula, unidade, nome, cpf, *_ = aluno
                st.success(f"Aluno encontrado: {nome} - CPF: {cpf}")
            else:
                st.error("Aluno não encontrado.")
        else:
            st.warning("Por favor, insira um valor para buscar.")

    if st.session_state.aluno_encontrado:
        matricula, nome, cpf, data, telefone, email, dados, unidade = st.session_state.aluno_encontrado[:8]

        st.text_input("Matrícula", value=matricula, disabled=True)
        st.text_input("Nome", value=nome, disabled=True)
        st.text_input("CPF", value=cpf, disabled=True)
        st.text_input("Unidade", value=unidade, disabled=True)

        data_pagamento = st.date_input("Data de Pagamento", value=datetime.today())
        plano = st.selectbox("Plano", ["Mensal", "Trimestral", "Semestral", "Anual"])
        valor_mensalidade = st.number_input("Valor da Mensalidade", min_value=0.0, step=0.01)

        if st.button("\U0001F4E5 Registrar Pagamento"):
            if valor_mensalidade <= 0:
                st.error("Por favor, insira um valor de mensalidade válido.")
            else:
                codigo = registrar_pagamento(matricula, unidade, nome, cpf, data_pagamento, plano, valor_mensalidade)
                if codigo:
                    st.success(f"Pagamento registrado com sucesso! Código da transação: {codigo}")
                    limpar_campos()
                else:
                    st.error("Falha ao registrar o pagamento.")
