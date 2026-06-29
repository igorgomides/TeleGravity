import os
import subprocess
import logging
import psutil
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
import google.generativeai as genai
from generate_invoice import create_invoice
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import tempfile
import re

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# State Management
class BotState:
    def __init__(self):
        self.current_directory = os.getcwd()
        self.provider = os.getenv("USE_PROVIDER", "gemini") # 'gemini', 'ollama', 'claude'

state = BotState()

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# LLM Provider Abstraction
class LLMProvider:
    def __init__(self):
        self.gemini_model = None
        if GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                # Model name might be gemini-2.0-flash or gemini-2.5-flash
                # Sticking to what user had but note 2.5-flash is likely 1.5 or 2.0
                self.model_name = 'gemini-2.5-flash' 
                self.gemini_model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                logging.error(f"Error configuring Gemini: {e}")
        
    def generate(self, prompt: str, history=None, system_instruction=None) -> str:
        if state.provider == "gemini" and self.gemini_model:
            try:
                model = self.gemini_model
                if system_instruction:
                    model = genai.GenerativeModel(self.model_name, system_instruction=system_instruction)
                
                if history:
                    chat = model.start_chat(history=history)
                    response = chat.send_message(prompt)
                else:
                    response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logging.error(f"Gemini error: {e}")
                if "429" in str(e):
                    return "ERROR:RATE_LIMIT"
                return f"ERROR:GEMINI:{e}"
        
        if state.provider == "claude":
            try:
                # Enforce saving outputs to the bot's web directory
                web_instruction = (
                    "SYSTEM INSTRUCTION: You are operating inside the Telegram Antigravity Bot. "
                    "The user views your work on a web dashboard hosting the local 'web/' directory. "
                    "Whenever the user asks you to create a design, document, report, script, HTML, or any artifact, "
                    "you MUST execute the necessary file creation command to save it directly to the 'web/' directory "
                    "locally (e.g., 'web/olabrasil_design.html' or 'web/report.md'). DO NOT output massive files in chat. "
                    "Once saved, tell the user the 'filename.ext' so they can see it on their dashboard.\n\n"
                )
                
                full_prompt = web_instruction + prompt
                if system_instruction:
                    full_prompt = f"System: {system_instruction}\n\n{full_prompt}"
                
                if history:
                    hist_text = ""
                    for m in history:
                        role = "Assistant" if m['role'] == 'model' else "User"
                        hist_text += f"{role}: {m['parts'][0]}\n"
                    full_prompt = f"{hist_text}User: {web_instruction}{prompt}"

                cmd = ["claude", "-p", full_prompt, "--dangerously-skip-permissions"]
                print(f"\n--- 🚀 INICIANDO TAREFA DO AGENTE ---", flush=True)
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=state.current_directory, bufsize=1)
                
                output_lines = []
                for line in process.stdout:
                    # Echo live to the terminal so the user can watch the agent "think"
                    print(f"🤖 AGENTE: {line}", end="", flush=True)
                    output_lines.append(line)
                    
                process.wait(timeout=300)
                print(f"--- ✅ A TAREFA FOI CONCLUÍDA (Código {process.returncode}) ---\n", flush=True)
                
                if process.returncode == 0:
                    return "".join(output_lines).strip()
                else:
                    return f"ERROR:CLAUDE:{''.join(output_lines).strip()}"
            except Exception as e:
                logging.error(f"Claude error: {e}")
                return f"ERROR:CLAUDE:{e}"
        
        # Fallback to Ollama if gemini fails or if specified
        try:
            import ollama
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"System: {system_instruction}\n\n{full_prompt}"
            
            # Simple history for Ollama
            if history:
                hist_text = ""
                for m in history:
                    role = "Assistant" if m['role'] == 'model' else "User"
                    hist_text += f"{role}: {m['parts'][0]}\n"
                full_prompt = f"{hist_text}User: {prompt}"

            response = ollama.generate(model=OLLAMA_MODEL, prompt=full_prompt)
            return response['response'].strip()
        except Exception as e:
            logging.error(f"Ollama error: {e}")
            return f"ERROR:OLLAMA:{e}"

llm = LLMProvider()

# Invoice Wizard States
INV_NAME, INV_ADDR, INV_PHONE, INV_EMAIL, INV_ITEM_DESC, INV_ITEM_QTY, INV_ITEM_PRICE, INV_TAX, INV_DUE = range(9)

# Authorization Decorator
def authorized_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if user_id != AUTHORIZED_USER_ID:
            logging.warning(f"Unauthorized access attempt by ID: {user_id}")
            return
        return await func(update, context)
    return wrapper

def execute_bash(command: str) -> str:
    """Executes a bash command with persistent directory awareness."""
    try:
        # Handle 'cd' manually to update state
        if command.startswith("cd "):
            new_path = command[3:].strip()
            # Handle absolute vs relative path
            target_dir = os.path.abspath(os.path.join(state.current_directory, new_path))
            if os.path.exists(target_dir) and os.path.isdir(target_dir):
                state.current_directory = target_dir
                return f"Directory changed to: {state.current_directory}"
            else:
                return f"Error: Directory not found: {new_path}"

        # Execute other commands in the current state directory
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=state.current_directory
        )
        return result.stdout or result.stderr or "Command executed with no output."
    except Exception as e:
        return f"Error executing: {str(e)}"

@authorized_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Antigravity Autonomous Bot Active*\n\n"
        "Available commands:\n"
        "/cmd <command> - Execute Bash command\n"
        "/agent <instruction> - Send mission to Antigravity\n"
        "/agents - List available Claude agents\n"
        "/ai <provider> - Switch AI (gemini, claude, ollama)\n"
        "/snapshot - Take iMac screenshot\n"
        "/status - View system status\n"
        "/kill - Stop active processes\n\n"
        "💡 *Tip*: You can also chat normally. I can decide to execute commands if necessary!",
        parse_mode='Markdown'
    )

async def send_long_text(update, text: str, parse_mode=None):
    """Sends text normally if under limit, otherwise as a .txt file to avoid Telegram errors."""
    if len(text) <= 4000:
        try:
            await update.message.reply_text(text, parse_mode=parse_mode)
        except Exception as e:
            if "can't parse" in str(e).lower() or "unclosed" in str(e).lower():
                # Fallback without markdown if parsing fails
                await update.message.reply_text(text)
            else:
                raise e
    else:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            clean_text = text.replace("```\n", "").replace("```", "")
            f.write(clean_text)
            temp_path = f.name
        
        with open(temp_path, 'rb') as doc:
            await update.message.reply_document(
                document=doc, 
                filename="response.txt", 
                caption="📄 A resposta era muito longa pro Telegram, então enviei como arquivo."
            )
        os.remove(temp_path)

@authorized_only
async def cmd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = " ".join(context.args)
    if not command:
        await update.message.reply_text("Usage: /cmd <command>")
        return

    output = execute_bash(command)
    
    # Truncate if too long
    if len(output) > 4000:
        output = output[:4000] + "\n... (truncated)"
        
    await update.message.reply_text(f"```\n{output}\n```", parse_mode='Markdown')

@authorized_only
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    status_msg = (
        f"📊 *System Status*\n"
        f"💻 CPU: {cpu}%\n"
        f"🧠 RAM: {ram}%\n"
        f"💾 Disk: {disk}%\n"
        f"📂 Folder: `{state.current_directory}`"
    )
    await update.message.reply_text(status_msg, parse_mode='Markdown')

@authorized_only
async def snapshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_path = "/tmp/snapshot.png"
    try:
        subprocess.run(["scrot", photo_path], check=True)
        with open(photo_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption="📸 Current iMac screenshot")
        os.remove(photo_path)
    except Exception as e:
        await update.message.reply_text(f"Error taking snapshot: {str(e)}")

@authorized_only
async def agent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instruction = " ".join(context.args)
    if not instruction:
        await update.message.reply_text("Usage: /agent <instruction>")
        return
    await update.message.reply_text(f"🚀 Antigravity Mission: `{instruction}`")

@authorized_only
async def kill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 Safety interrupt triggered.")
    logging.info("Safety switch /kill triggered.")

@authorized_only
async def ai_switch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    provider = " ".join(context.args).lower().strip()
    valid_providers = ["gemini", "claude", "ollama"]
    
    if not provider or provider not in valid_providers:
        await update.message.reply_text(f"Usage: /ai <provider>\nValid values: {', '.join(valid_providers)}\nCurrent: {state.provider}")
        return
        
    state.provider = provider
    await update.message.reply_text(f"✅ AI provider switched to: *{provider}*", parse_mode='Markdown')

def get_agent_metadata(filepath):
    meta = {
        "desc": "Agente especialista pronto para receber suas instruções.",
        "clean_name": None,
        "identity": None
    }
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(4096) 
            
            desc_match = re.search(r'description:\s*"?([^"\n]+)"?', content)
            if desc_match:
                meta["desc"] = desc_match.group(1).strip()
                
            # Try to get the clean name from the agent block
            name_match = re.search(r'agent:.*?name:\s*"?([^"\n]+)"?', content, re.DOTALL)
            if name_match:
                meta["clean_name"] = name_match.group(1).strip()
                
            # Try to get the formal identity to use as authority bio
            identity_match = re.search(r'identity:\s*"?([^"\n]+)"?', content)
            if identity_match:
                meta["identity"] = identity_match.group(1).strip()
    except:
        pass
    return meta

AUTHORITY_BIOS = {
    "ray-dalio": "Bilionário e fundador da Bridgewater. Criador do método 'Princípios' e especialista em decisões.",
    "charlie-munger": "Lendário investidor e ex-CFO da Berkshire Hathaway. Mestre atemporal em Modelos Mentais.",
    "reid-hoffman": "Co-fundador do LinkedIn e investidor lendário. Mestre global em Blitzscaling e efeitos de rede.",
    "simon-sinek": "Autor best-seller do 'Comece pelo Porquê'. Especialista humanista em liderança organizacional.",
    "peter-thiel": "Co-fundador do PayPal. Pensador contrariano e arquiteto-mestre de monopólios corporativos.",
    "naval-ravikant": "Investidor anjo icônico (Twitter) e filósofo moderno sobre alavancagem ('Productize Yourself').",
    "derek-sivers": "Fundador da CD Baby. Mestre do essencialismo e de focar exclusivamente nas escolhas 'Hell Yeah'.",
    "brene-brown": "Pesquisadora PhD. Autora nº1 sobre coragem, cultura da empatia e poder na vulnerabilidade.",
    "yvon-chouinard": "Lenda americana, criador da Patagonia e pioneiro indiscutível em capitalismo verde consciente.",
    "patrick-lencioni": "Mago do design organizacional corporativo, resolve os '5 Desafios das Equipes'.",
    "marty-neumeier": "Autoridade suprema em Estratégia Radical de Marcas ('The Brand Gap').",
    "al-ries": "Cérebro por trás da Teoria do Posicionamento, tese fundadora do marketing corporativo moderno.",
    "david-aaker": "O 'Pai do Branding', criador do modelo científico de Brand Equity adotado em escala global.",
    "kevin-keller": "Professor emérito. Pioneiro do modelo de Ressonância (CBBE) usado nas Fortune 500.",
    "jean-noel-kapferer": "Expertise mor global na gestão de identidade corporativa (Prisma) e luxo inalcançável.",
    "donald-miller": "Consultor genial. Usa elementos de ficção no marketing de resposta via 'StoryBrand'.",
    "alina-wheeler": "Doutrinadora incontestável. Seu livro dita os manuais de padronização visual há 20 anos.",
    "emily-heyward": "Mente criativa por trás da agência Red Antler. Arquiteta do design de Unicórnios tecnológicos.",
    "denise-yohn": "Autora do aclamado 'What Great Brands Do'. Focada em alinhar a marca pura e a cultura.",
    "byron-sharp": "Cientista pesquisador (Ehrenberg-Bass). Destruiu mitos focando no alcance empírico sem rodeios.",
    "eugene-schwartz": "Dinossauro legendário da resposta direta; ensinou a casar promessas à 'Consciência do Mercado'.",
    "gary-halbert": "O mais infame e mortal Copywriter de cartas pelo correio da história. Puramente focado em conversão.",
    "gary-bencivenga": "Evangelista da Conversão Baseada em Provas. Copywriter com as maiores taxas de sucesso da era.",
    "david-ogilvy": "O autêntico 'Pai da Propaganda', forjador da Madison Avenue guiada por pesquisas factuais.",
    "dan-kennedy": "A lenda do Marketing Magnético. Sua persuasão arquitetou o modelo multi-milionário de funis agressivos.",
    "claude-hopkins": "A rocha base do copywriting há um século ('Scientific Advertising', 1923).",
    "robert-collier": "Ilusionista mental, cunhou 'Entre na conversa que já está acontecendo na cabeça do prospecto'.",
    "john-carlton": "Fundador do 'Storytelling de Ruas', táticas implacáveis do submundo do marketing selvagem.",
    "jim-rutz": "Mudou toda a indústria da saúde e finanças com fascinações e teasers longos incrivelmente persuasivos.",
    "joe-sugarman": "Escavou trunfos através de narrativas longas nos catálogos BluBlocker nas décadas de 70-80.",
    "stefan-georgi": "Recordista contemporâneo (bilionário de vendas). Criador da metodologia de Copy in-a-box RMBC.",
    "russell-brunson": "Fundador do ClickFunnels. Revisitou a lenda do marketing para arquitetar os Funis de Storytelling digital.",
    "frank-kern": "O lobo original das origens do Marketing da internet, arquiteto das famosas sequências de tensão.",
    "ben-settle": "Patriarca sombrio do 'Email Marketing de Entretenimento'. Sabe extrair vendas todos os dias por texto.",
    "dan-koe": "Fenômeno da 'Creator Economy' moderna. Usa design existencial estoico para monetizar mentes.",
    "jon-benson": "O Pai incontestável da 'VSL' (Carta em Vídeo), que pavimentou caminhos multi-bilionários no tráfego.",
    "ry-schwartz": "Pioneiro do Micro-Copy focado nas micro-conversões emocionais dos maiores lançamentos mundiais.",
    "todd-brown": "Cirurgião frio de Aquisição (O Engenheiro das 'Big Ideas' do E5 Method).",
    "parris-lampropoulos": "Estudioso recluso, mestre absoluto de cartas de saúde que demoram meses para serem minuciosamente escritas.",
    "clayton-makepeace": "O Copywriter mais bem pago da história moderna, assustadoramente bom com lógicas financeiras puras.",
    "david-deutsch": "Pupilo das maiores agências clássicas. O mestre supremo dos mistérios (Fascinações de Bullet Points).",
    "andre-chaperon": "O artista genial invisível por trás do conceito cult de 'Soap Opera Sequences' e narrativas infinitas auto-responsivas.",
    "omar-santos": "Engenheiro-Principal Cisco, autor best-seller focado em defesa estrutural pesada (Hardening).",
    "georgia-weidman": "Gênia ofensiva, dona da maior penetração corporativa em testes via dispositivos móveis do mercado.",
    "peter-kim": "Autor do The Hacker Playbook; táticas clandestinas pesadamente testadas contra Enterprise firewalls.",
    "marcus-carey": "Fundador visionário Threatcare. Perito em dissecção de defesas e red-teaming (Simulação Agressiva).",
    "jim-manico": "Autoridade blindada. Através do OWASP, reescreveu a cultura do código-seguro em servidores cloud.",
    "chris-sanders": "Caçador veterano de ameaças invisíveis (Threat Hunts), dominou análise pericial rigorosa de tráfego de rede livre.",
    "avinash-kaushik": "Evangelista Original Google; dissecou a dor das vaidades do tráfego com métricas cirúrgicas brutalmente reais.",
    "sean-ellis": "O padrinho que imortalizou a engenharia Growth Hacking, testando e explodindo Unicórnios precoces nos EUA.",
    "peter-fader": "Oráculo da Wharton. Provou matematicamente o imperativo Customer Lifetime Value e rentabilidades atípicas.",
    "nick-mehta": "CEO-Evangelista, escreveu sozinha o evangelho corporativo chamado: Customer Success Corporativo em Saas.",
    "david-spinks": "Decodificou antropologicamente as mecânicas de conversão em tribos digitais (Comunidades).",
    "wes-kao": "Líder e Fundadora (Maven). Criou o nicho formidável nativo de cursos co-criados baseados em Cohort de Alto Valor.",
    "brad-frost": "Cientista Nuclear do CSS: Criou o clássico indiscutível 'Atomic Design' utilizado por megacorporações do planeta.",
    "dan-mall": "Maestro dos 'Design Systems'. Foca menos nos píxeis, muito mais nos fluxos arquiteturais para times massivos em escala global.",
    "dave-malouf": "Filósofo de ponta das eficiências de Produto de Operação, unindo a psicologia de Design e velocidade comercial (DesignOps).",
    "hormozi": "Alex Hormozi ($100M). Empreendedor feroz, empacotando mecânicas puras de atração/ofertas impossíveis matematicamente provadas para conversão brutal e irreversível.",
    "joseph-campbell": "O Gênio Decodificador do subconsciente (Mitos e Arquétipos Universais nas sombras do tempo) utilizado pela Disney.",
    "blake-snyder": "Arquiteto de Filmes (Save The Cat) que organizou as engrenagens de blocos emotivos invisíveis dos roteiros bilionários comerciais hollywoodianos originais.",
    "dan-harmon": "Gênio Louco Matemático. Transcreveu todo seu brilhantismo narrativo abstratante dentro das regras do monomito estruuralizado infalível: 'O Círculo da História' irônico e existencialista atemporal do mundo pós moderno irônico.",
    "shawn-coyne": "Cirurgião de livros, editor rigoroso da Bíblia estrutural literária moderna ('Story Grid') com mecânicas cirúrgicas de tensão narrativa calculadas em números puros absolutos exatos.",
    "nancy-duarte": "Consultora Suprema da Inteligência do Storytelling do Vale do Silício moderno. Ela arquiteta os discursos bilionários precisos corporativos mais impactantes da América (a mecânica oculta secreta de Steve Jobs em discursos estruturalizados).",
    "matthew-dicks": "O Ladrão Supremo de Atenções diárias (Moth StorySlam). Treina conversões focadas em memórias orais micro-pessoais vulneráveis para apresentações de palcos impactantes inabaláveis carismáticas magnéticas hipnóticas.",
    "kindra-hall": "Decodificadora comercial das historietas que cimentam e fixam alicerces leais irremovíveis de fidelizações absolutas inquebráveis ​​para marcas nativas originais e bilionárias independentes orgânicas (Value storytelling).",
    "marshall-ganz": "Teórico político magistral americano ativista tático que fundou os modelos invisíveis ocultos absolutos ('Public Narrative') do comitê Obama para movimentos sociais coletivos autônomos e irresistíveis políticos históricos monumentais irreversíveis.",
    "park-howell": "Racionalista Pragmático focado exclusivamente no framework tático pragmático ('Business of Story') formatando ROI em palavras, narrativas purificadas orientantes exatas estratégicas irrecusáveis para pitchs perfeitos orquestrados perfeitamente milimétricos diretos exatos precisos inabaláveis implacáveis exatos.",
    "oren-klaff": "Máquina de capitalizações ('Pitch Anything'). Manipulador frio calculista puro de 'Framos (Quadros) Mentais' e neurofinanças de primatas primitivas animalescas reptilianas humanas focadas unicamente visceralmente na obtenção purista de alfas de dominações intelectuais imediatas exatas letais diretas instantâneas esmagadoras irreversíveis absolutistas implacáveis focadas perfeitamente precisas brutais puras calculistas estritamente lógicas impecáveis impecáveis exatas precisões definitivas",
    "keith-johnstone": "Tático existencial dos 'Status de Poder Sub-Textuais' teatrais e psicólogos. Como os humanos sinalizam instintivamente controle primata oculto por linguagem silenciosa inconsciente perfeitamente lida milimetricamente precisa brutal pura animal.",
    "molly-pittman": "Supercérebro de Aquisições metódicas nativas da SmartMarketer. Escalou metodologias testadas à pura exaustão calculada implacavelmente perfeitas precisas irrecusáveis absolutas completas puras pragmáticas lógicas frias.",
    "nicholas-kusmich": "Dominante das exclusividades e altíssimos tickets invisíveis orgânicos segmentados em campanhas perversamente calibradas milionárias exatas puras impecáveis infalíveis letais precisões calculistas brutais de tráfego ultra seletos do Face.",
    "depesh-mandalia": "Escalador feroz Europeu absoluto agressivo implacável de E-commerces. Controla ecossistemas FacebookAds como um arquiteto macro agressivo veloz implacável focado metodicamente em volumes colossais massivos absurdos escaláveis brutos imensuráveis orgânicos agressivos implacáveis precisões calculadas letais globais maciços puros absolutos agressivamente exatos implacáveis brutos irreais absolutos frios exatos massivos avassaladores épicos",
    "ralph-burns": "Arquiteto perverso de Mídia Omni-Channel (Tier 11) que domina a captura infinita impiedosa da malha de atenção em múltiplas frentes cruzadas exatas perfeitamente alinhadas calculistas avassaladoras puras diretas focadas completas definitivas letais completas avassaladores precisões imutáveis irreversíveis.",
    "tom-breeze": "Imperador Científico Supremo irrefutável do Tráfego Implacável Direto Nativo Naturo do YouTubeAds, criando mecânicas de conversão em tempo real in-stream em massa absolutas colossais infinitas massivas cirúrgicas absolutas de CPA irrecusáveis letais completas implícitas",
    "kasim-aslam": "Neurocientista do Google Ads purista algorítmico, manipulador dos bastidores autômatos puristas mecânicos automatizados de IAs Google para retornos colossais absurdos agressivos escaláveis monstruosos esmagadores avassaladores nativos implacáveis absolutos diretos colossais mecânicos estritos puros lógicos inabaláveis algorítmicos cruéis puristas absolutistas inquebráveis definitivos maciços implacáveis.",
    "pedro-sobral": "Baluarte Brasileiro Absoluto. Catedrático insubstituível que formatou inteiramente todo o país como O Mestre Frio e Calculista dos Submudos de Distribuição e contingência, planilhamentos agressivos e brutalidades pragmáticas em MetaAds exatos puros inabaláveis inquebráveis absolutos impiedosos totais completos cruéis calculistas frios definitivos avassaladores avassaladores letais.",
}

def extract_file_meta(filepath):
    """Extract title, description and type tag from an HTML work file."""
    import re as _re
    title, desc, wtype, wagent = None, None, None, None
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            raw = fh.read(4000)
        m = _re.search(r'<title[^>]*>(.*?)</title>', raw, _re.IGNORECASE | _re.DOTALL)
        if m:
            title = _re.sub(r'<[^>]+>', '', m.group(1)).strip()
        m = _re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', raw, _re.IGNORECASE)
        if m:
            desc = m.group(1).strip()
        m = _re.search(r'<meta[^>]+name=["\']work-type["\'][^>]+content=["\'](.*?)["\']', raw, _re.IGNORECASE)
        if m:
            wtype = m.group(1).strip()
        m = _re.search(r'<meta[^>]+name=["\']work-agent["\'][^>]+content=["\'](.*?)["\']', raw, _re.IGNORECASE)
        if m:
            wagent = m.group(1).strip()
    except Exception:
        pass
    return {
        "title": title or filepath,
        "desc": desc or "Clique para visualizar o trabalho completo.",
        "type": wtype or "Documento",
        "agent": wagent or "",
    }

def generate_dashboard_html():
    import glob
    agents_dir = os.path.expanduser("~/.claude/agents")
    categories = {}
    
    # Parse agents
    if os.path.exists(agents_dir):
        for md_file in glob.glob(os.path.join(agents_dir, "*.md")):
            basename = os.path.basename(md_file)
            agent_id = basename.replace(".md", "")
            
            meta = get_agent_metadata(md_file)
            desc = meta["desc"]
            clean_name = meta["clean_name"] if meta["clean_name"] else agent_id.replace('-', ' ').title()
            identity = meta["identity"]
            
            parts = agent_id.split('-')
            cat = "Outros"
            if len(parts) > 1:
                if "brand-squad" in agent_id: cat = "Brand Squad"
                elif "c-level-squad" in agent_id: cat = "C-Level Squad"
                elif "copy-squad" in agent_id: cat = "Copy Squad"
                elif "data-squad" in agent_id: cat = "Data Squad"
                elif "design-squad" in agent_id: cat = "Design Squad"
                elif "hormozi-squad" in agent_id: cat = "Hormozi Squad"
                elif "advisory-board" in agent_id: cat = "Advisory Board"
                elif "traffic-masters" in agent_id: cat = "Traffic Masters"
                elif "claude-code-mastery" in agent_id: cat = "Claude Mastery"
                elif "cybersecurity" in agent_id: cat = "Cybersecurity"
                elif "storytelling" in agent_id: cat = "Storytelling"
                elif "movement" in agent_id: cat = "Movement"
            
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "id": agent_id, 
                "name": clean_name, 
                "desc": desc,
                "identity": identity
            })
    
    # Parse work files in web/
    try:
        work_files = [f for f in os.listdir("web") if not f.startswith('.') and f != "index.html" and f != "agentes.html" and f != "dashboard.html"]
        work_files.sort()
    except:
        work_files = []
    
    # Build HTML
    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TeleGravity - Bots and Agents</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        h2 { color: #e67e22; margin-top: 30px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        
        .work-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; padding: 0; margin: 0; }
        .work-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 18px 20px; display: flex; flex-direction: column; gap: 10px; transition: box-shadow .2s, border-color .2s; text-decoration: none; color: inherit; }
        .work-card:hover { box-shadow: 0 4px 16px rgba(52,152,219,.15); border-color: #3498db; }
        .work-card-type { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #fff; background: #e67e22; padding: 3px 10px; border-radius: 100px; width: fit-content; }
        .work-card-title { font-size: 1em; font-weight: 700; color: #2c3e50; line-height: 1.3; }
        .work-card-desc { font-size: 0.85em; color: #7f8c8d; line-height: 1.5; flex: 1; }
        .work-card-footer { display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid #f0f0f0; }
        .work-card-agent { font-size: 0.75em; color: #bbb; }
        .work-card-cta { font-size: 0.8em; font-weight: 700; color: #3498db; }
        
        .agent-list { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 15px; }
        .agent-item { background: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
        .agent-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 15px; background-color: #fafafa; cursor: pointer; transition: 0.2s; font-weight: bold; }
        .agent-header:hover { background-color: #f0f0f0; }
        .agent-body { padding: 15px; background-color: #fff; display: none; border-top: 1px solid #eee; color: #555; }
        .agent-desc { font-style: italic; margin-bottom: 10px; color: #666; font-size: 0.95em; }
        .agent-copy { background: #3498db; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.9em; font-weight: bold; margin-top: 10px; }
        .agent-copy:hover { background: #2980b9; }
        .footer { margin-top: 40px; font-size: 0.8em; color: #aaa; text-align: center; }
    </style>
    <script>
        function toggleAgent(el) {
            const body = el.nextElementSibling;
            body.style.display = body.style.display === 'block' ? 'none' : 'block';
        }
        function copyAgent(btn, name) {
            navigator.clipboard.writeText(name);
            btn.innerText = 'Copiado!';
            setTimeout(() => { btn.innerText = 'Copiar Comando'; }, 2000);
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>🌐 TeleGravity - Bots and Agents</h1>
        
        <!-- MODULE 1: Work Files -->
        <h2>📁 Trabalhos dos Agentes</h2>
        <p style="font-size:0.9em; color:#7f8c8d;">Arquivos gerados pelos agentes na pasta web do bot (clique para visualizar):</p>
        <div class="work-grid">
"""
    if work_files:
        for f in work_files:
            fpath = os.path.join("web", f)
            meta = extract_file_meta(fpath)
            html += f"""<a class="work-card" href="/{f}">
                <span class="work-card-type">{meta['type']}</span>
                <div class="work-card-title">{meta['title']}</div>
                <div class="work-card-desc">{meta['desc']}</div>
                <div class="work-card-footer">
                    <span class="work-card-agent">{meta['agent']}</span>
                    <span class="work-card-cta">Visualizar →</span>
                </div>
            </a>"""
    else:
        html += "<p style='color:#bbb; font-size:0.9em;'>Nenhum trabalho encontrado ainda.</p>"

    html += """
        </div>
        
        <!-- MODULE 2: Agents List -->
        <h2>🤖 Dicionário de Agentes</h2>
        <p style="font-size:0.9em; color:#7f8c8d;">Catálogo com as descrições e propósitos de todos os seus agentes locais disponíveis. Clique neles para expandir.</p>
"""
    
    for cat in sorted(categories.keys()):
        html += f"<h3>{cat}</h3><div class='agent-list'>"
        # sort agents alphabetically map
        agents_sorted = sorted(categories[cat], key=lambda x: x['name'])
        for agent in agents_sorted:
            name = agent['name'] if agent['name'] else agent['id'].replace('-', ' ').title()
            agent_id = agent['id']
            agent_desc = agent['desc'] if agent['desc'] else "Agente especialista"
            
            authority_tags = []
            
            # 1. Fallback to generic identity parsed from YAML
            if agent.get('identity'):
                authority_tags.append(agent['identity'])
                
            # 2. Add manual BIOS matching
            for known_key, bio in AUTHORITY_BIOS.items():
                if known_key in agent_id.lower():
                    if bio not in authority_tags:
                        authority_tags.insert(0, bio)
            
            if authority_tags:
                agent_desc += "<br><br><span style='color: #2980b9; font-size: 0.9em; line-height: 1.4; display:block; padding: 10px; background: #e8f6fc; border-radius: 6px; border-left: 4px solid #3498db;'>" + "<br>".join([f"<strong>🏆 Autoridade:</strong> {t}" for t in authority_tags]) + "</span>"
                
            html += f"""
            <div class="agent-item">
                <div class="agent-header" onclick="toggleAgent(this)">
                    <span>⚡ {name}</span>
                    <span style="font-size:0.8em; color:#bbb;">▼</span>
                </div>
                <div class="agent-body">
                    <div class="agent-desc">{agent_desc}</div>
                    <p style="font-size:0.9em; margin:0; margin-top:15px; color:#444;">Formato para Telegram:</p>
                    <code style="background:#f4f4f4; padding:5px 8px; border-radius:3px; display:inline-block; font-size:0.9em; margin-top:5px; color:#c0392b; font-weight:bold;">Peça para @{agent_id} ...</code>
                    <br>
                    <button class="agent-copy" onclick="copyAgent(this, '@{agent_id}')">Copiar Comando</button>
                </div>
            </div>
            """
        html += "</div>"

    html += """
        <div class="footer">Antigravity Autonomous Bot | Porta 8090</div>
    </div>
</body>
</html>
"""
    return html

def start_web_server():
    os.makedirs("web", exist_ok=True)
    class DashboardHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory="web", **kwargs)
            
        def do_GET(self):
            if self.path == '/' or self.path == '/index.html' or self.path == '/dashboard.html':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                # Dynamically generate dashboard
                html = generate_dashboard_html()
                self.wfile.write(html.encode('utf-8'))
            else:
                super().do_GET()
                
    server = HTTPServer(('0.0.0.0', 8090), DashboardHandler)
    server.serve_forever()

# Start background server
threading.Thread(target=start_web_server, daemon=True).start()

@authorized_only
async def list_agents_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Gerando o Dashboard Analítico mais recente...")
    
    os.makedirs("web", exist_ok=True)
    html_content = generate_dashboard_html()
    
    # Save a static snapshot for Telegram sending
    filepath = "web/dashboard_offline.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    await update.message.reply_text(
        "🌐 Seu Painel Central com as Descrições e Arquivos está 100% Online!\n\n"
        "Acesse por aqui:\n"
        "👉 http://localhost:8090\n\n"
        "*(Se estiver na rua usando 4G, utilize http://gomides.duckdns.org:8090)*\n\n"
        "📄 Cópia offline anexada abaixo:"
    )
    with open(filepath, "rb") as doc:
        await update.message.reply_document(document=doc, filename="dashboard.html")

@authorized_only
async def invoice_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['invoice_items'] = []
    await update.message.reply_text("📄 *Invoice Wizard Started*\nTo cancel at any time, type /cancel.\n\nFor which company/client is this invoice?", parse_mode='Markdown')
    return INV_NAME

@authorized_only
async def invoice_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Invoice generation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

@authorized_only
async def invoice_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['invoice_client_name'] = update.message.text
    await update.message.reply_text("What is the client's address? (Type '-' or 'none' to skip)")
    return INV_ADDR

@authorized_only
async def invoice_addr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['invoice_client_address'] = update.message.text
    await update.message.reply_text("What is the client's phone number? (Type '-' or 'none' to skip)")
    return INV_PHONE

@authorized_only
async def invoice_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['invoice_client_phone'] = update.message.text
    await update.message.reply_text("What is the client's email address? (Type '-' or 'none' to skip)")
    return INV_EMAIL

@authorized_only
async def invoice_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['invoice_client_email'] = update.message.text
    await update.message.reply_text("📝 What is the description of the item/service?\n\nIf you have added all items and want to finish, type `done`.", parse_mode='Markdown')
    return INV_ITEM_DESC

@authorized_only
async def invoice_item_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() in ['done', 'fim']:
        if not context.user_data.get('invoice_items'):
            await update.message.reply_text("You haven't added any items. Please add at least one description or type /cancel.")
            return INV_ITEM_DESC
        await update.message.reply_text("Would you like to include HST tax (13%)? (yes/no)")
        return INV_TAX
        
    if text.lower() in ['fix', 'corrigir']:
        if context.user_data.get('invoice_items'):
            removed_item = context.user_data['invoice_items'].pop()
            await update.message.reply_text(f"🗑️ The last item ({removed_item['desc']}) has been removed.\n\n📝 What is the description of the item/service? Or type `done`.", parse_mode='Markdown')
        else:
            await update.message.reply_text("There are no items to fix. Please add an item first.")
        return INV_ITEM_DESC
    
    context.user_data['temp_desc'] = text
    await update.message.reply_text("🔢 What is the quantity for this item?")
    return INV_ITEM_QTY

@authorized_only
async def invoice_item_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        qty = int(text)
        context.user_data['temp_qty'] = qty
        await update.message.reply_text("💰 What is the unit price for this item? (e.g., 150, 50.50)")
        return INV_ITEM_PRICE
    except ValueError:
        await update.message.reply_text("❌ Invalid quantity. Please enter a valid whole number (e.g., 1, 2, 10).")
        return INV_ITEM_QTY

@authorized_only
async def invoice_item_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        price = float(text.replace('$', '').replace('CAD', '').strip())
        desc = context.user_data['temp_desc']
        qty = context.user_data['temp_qty']
        
        context.user_data['invoice_items'].append({'desc': desc, 'qty': qty, 'price': price})
        
        await update.message.reply_text(f"✅ Item added! We have {len(context.user_data['invoice_items'])} item(s) so far.\n\n📝 What is the description of the NEXT item?\n\nTo fix/remove the last item, type `fix`.\nWhen finished, type `done`.", parse_mode='Markdown')
        return INV_ITEM_DESC
    except ValueError:
        await update.message.reply_text("❌ Invalid price format. Please enter a valid number (e.g., 150, 50.50).")
        return INV_ITEM_PRICE

@authorized_only
async def invoice_tax(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text in ['yes', 'y', 'sim', 's']:
        context.user_data['invoice_tax_rate'] = 0.13
    else:
        context.user_data['invoice_tax_rate'] = 0.0
    await update.message.reply_text("What is the due date? (e.g., 30 days, Upon Receipt, 15/04/2026)")
    return INV_DUE

@authorized_only
async def invoice_due(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['invoice_due_date'] = update.message.text
    await update.message.reply_text("⏳ Generating invoice...")
    
    address = context.user_data.get('invoice_client_address', '')
    phone = context.user_data.get('invoice_client_phone', '')
    email = context.user_data.get('invoice_client_email', '')
    
    full_address = address if address.lower() not in ['none', 'na', 'n/a', '-'] else ""
    if phone.lower() not in ['none', 'na', 'n/a', '-', '']:
        full_address += f"\nPhone: {phone}"
    if email.lower() not in ['none', 'na', 'n/a', '-', '']:
        full_address += f"\nEmail: {email}"
    
    try:
        pdf_path = create_invoice(
            client_name=context.user_data['invoice_client_name'],
            client_address=full_address.strip(),
            items=context.user_data['invoice_items'],
            tax_rate=context.user_data['invoice_tax_rate'],
            due_date=context.user_data['invoice_due_date']
        )
        
        # Upload to website if configured
        website_url = os.getenv("WEBSITE_URL")
        secret_key = os.getenv("FLASK_SECRET_KEY")
        if website_url and secret_key:
            try:
                import requests
                # calculate total amount
                subtotal = sum(item['qty'] * item['price'] for item in context.user_data['invoice_items'])
                total_due = subtotal * (1 + context.user_data['invoice_tax_rate'])
                
                # extract invoice number
                filename = os.path.basename(pdf_path)
                match = re.search(r'(INV-\d{8}-\d{4})', filename)
                invoice_number = match.group(1) if match else "INV-UNKNOWN"
                
                with open(pdf_path, 'rb') as f:
                    files = {'file': (filename, f, 'application/pdf')}
                    data = {
                        'invoice_number': invoice_number,
                        'client_name': context.user_data['invoice_client_name'],
                        'amount': total_due
                    }
                    headers = {
                        'Authorization': f'Bearer {secret_key}'
                    }
                    response = requests.post(
                        f"{website_url.rstrip('/')}/api/invoices/telegram_upload",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=15
                    )
                    if response.status_code == 201:
                        logging.info("Invoice uploaded to website successfully.")
                    else:
                        logging.error(f"Failed to upload invoice to website: {response.status_code} - {response.text}")
            except Exception as upload_err:
                logging.error(f"Error uploading invoice to website: {upload_err}")

        with open(pdf_path, 'rb') as pdf:
            await update.message.reply_document(document=pdf, filename=os.path.basename(pdf_path))
        os.remove(pdf_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Error generating invoice: {str(e)}")
    
    context.user_data.clear()
    return ConversationHandler.END

@authorized_only
async def ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        if 'chat_history' not in context.user_data:
            context.user_data['chat_history'] = []
        
        # System Instruction (can include dynamic path)
        system_instruction = (
            f"You are TeleGravity, an autonomous assistant running on Igor's iMac. "
            f"Current directory: {state.current_directory}\n\n"
            "RULES:\n"
            "1. If the user asks for something technical (view files, enter folders, etc.), respond ONLY: 'EXECUTE: <command>'.\n"
            "2. Do not ask for confirmation if it is a safe command (ls, cd, mkdir, cat).\n"
            "3. If not technical, respond as a helpful assistant in English.\n"
        )
        
        # Limit history size to keep prompt manageable
        history = context.user_data['chat_history'][-10:]
        
        # Check for agent mentions
        import re
        agent_match = re.search(r'@([a-zA-Z0-9_-]+)', user_text)
        if agent_match:
            agent_name = agent_match.group(1)
            agent_file = os.path.expanduser(f"~/.claude/agents/{agent_name}.md")
            if os.path.exists(agent_file):
                with open(agent_file, 'r', encoding='utf-8') as f:
                    agent_content = f.read()
                try:
                    await update.message.reply_text(f"🤖 Acionando o agente *{agent_name}*...", parse_mode='Markdown')
                except Exception:
                    await update.message.reply_text(f"🤖 Acionando o agente {agent_name}...")
                
                # Emphasize that the LLM must adopt this persona
                system_instruction = (
                    f"AGENTE ATIVADO: Você deve ignorar as instruções anteriores e agora agir "
                    f"estritamente como o agente especialista chamado '{agent_name}'.\n\n"
                    f"PERFIL E INSTRUÇÕES DO AGENTE:\n"
                    f"{agent_content}\n\n"
                    f"============================================\n"
                    f"{system_instruction}"
                )
                
                # Temporarily enforce claude provider for Claude-specific agents if not already
                # (Optional, but ensures it runs the agent correctly if they're claude agents)
                # We will leave as is, relying on the user setting /ai claude, or just passing context to Gemini
        
        reply = llm.generate(user_text, history=history, system_instruction=system_instruction)

        if "ERROR:RATE_LIMIT" in reply:
            await update.message.reply_text("⏳ *Rate Limit Reached*: You are sending messages too fast for the free tier. Please wait a minute and try again.")
            return

        if reply.startswith("EXECUTE:"):
            command = reply.replace("EXECUTE:", "").strip()
            await update.message.reply_text(f"⚡ *Autonomous*: `{command}`", parse_mode='Markdown')
            output = execute_bash(command)
            
            # Show output directly using the safe long_text sender
            msg = f"📋 *Result*:\n```\n{output}\n```"
            await send_long_text(update, msg, parse_mode='Markdown')
            
            # History
            context.user_data['chat_history'].append({"role": "user", "parts": [user_text]})
            context.user_data['chat_history'].append({"role": "model", "parts": [reply + "\n\nOutput: " + output[:500]]})
        else:
            await send_long_text(update, reply)
            context.user_data['chat_history'].append({"role": "user", "parts": [user_text]})
            context.user_data['chat_history'].append({"role": "model", "parts": [reply]})
            
    except Exception as e:
        await update.message.reply_text(f"❌ AI processing error: {str(e)}")

if __name__ == '__main__':
    if not TOKEN:
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cmd", cmd_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("snapshot", snapshot_handler))
    app.add_handler(CommandHandler("agent", agent_handler))
    app.add_handler(CommandHandler("agents", list_agents_handler))
    app.add_handler(CommandHandler("ai", ai_switch_handler))
    app.add_handler(CommandHandler("kill", kill_handler))
    
    invoice_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('invoice', invoice_start)],
        states={
            INV_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_name)],
            INV_ADDR: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_addr)],
            INV_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_phone)],
            INV_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_email)],
            INV_ITEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_item_desc)],
            INV_ITEM_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_item_qty)],
            INV_ITEM_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_item_price)],
            INV_TAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_tax)],
            INV_DUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_due)],
        },
        fallbacks=[CommandHandler('cancel', invoice_cancel)],
    )
    app.add_handler(invoice_conv_handler)
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ai_handler))

    print("Bot running...")
    app.run_polling()
