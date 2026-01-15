import json, os, requests, base64, threading, uuid
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import AsyncImage
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock

# --- CONFIGURAÇÕES DO LUCAS ---
API_KEY_IMGBB = "fb91ccfe94c5c8e12f6d909a901ffdb6" 
LINK_BASE_FIREBASE = "https://treebookpro-default-rtdb.firebaseio.com/arvores"

class Card(BoxLayout):
    def __init__(self, arvore, id_fb, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 600 
        self.padding = 15
        self.spacing = 10
        self.id_fb = id_fb
        self.app_ref = app_ref
        
        # Logica de Like Único
        curtidas_dict = arvore.get('curtidas_usuarios', {})
        self.ja_curtiu = self.app_ref.meu_id in curtidas_dict

        with self.canvas.before:
            Color(0.12, 0.18, 0.12, 1) 
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[20,])
        self.bind(pos=self.update_rect, size=self.update_rect)

        # Cabeçalho
        header = BoxLayout(size_hint_y=0.1)
        header.add_widget(Label(text=arvore.get('nome', '').upper(), font_size='18sp', bold=True, color=(0.4, 1, 0.4, 1)))
        btn_del = Button(text="X", size_hint_x=0.15, background_color=(0.8, 0.2, 0.2, 1))
        btn_del.bind(on_press=lambda x: self.app_ref.confirmar_exclusao(self.id_fb))
        header.add_widget(btn_del)
        self.add_widget(header)
        
        # Imagem
        if arvore.get('foto_url'):
            self.add_widget(AsyncImage(source=arvore['foto_url'], size_hint_y=0.5))
        
        # Descrição
        self.add_widget(Label(text=arvore.get('descricao', ''), size_hint_y=0.2, halign="center", italic=True))

        # Rodapé
        footer = BoxLayout(size_hint_y=0.2, spacing=10)
        num_likes = arvore.get('likes', 0)
        cor_botao = (0.3, 0.3, 0.3, 1) if self.ja_curtiu else (0.8, 0.2, 0.2, 1)
        
        self.btn_like = Button(text=f"CURTIDAS: {num_likes}", background_color=cor_botao, bold=True)
        self.btn_like.bind(on_press=lambda x: self.app_ref.curtir_na_nuvem(self.id_fb, num_likes, self.ja_curtiu))
        
        btn_share = Button(text="ENVIAR", background_color=(0.1, 0.6, 0.3, 1), bold=True)
        btn_share.bind(on_press=lambda x: self.app_ref.compartilhar(arvore))
        
        footer.add_widget(self.btn_like)
        footer.add_widget(btn_share)
        self.add_widget(footer)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class TreeBook(App):
    def build(self):
        self.meu_id = self.obter_id_celular()
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=5)
        
        topo = BoxLayout(size_hint_y=0.12, orientation='vertical')
        linha1 = BoxLayout()
        linha1.add_widget(Label(text="TREEBOOK V1.2", font_size='22sp', bold=True, color=(0.4, 1, 0.4, 1)))
        btn_add = Button(text="+ POSTAR", size_hint_x=0.4, background_color=(0, 0.5, 0.2, 1), bold=True)
        btn_add.bind(on_press=self.abrir_painel)
        linha1.add_widget(btn_add)
        topo.add_widget(linha1)
        topo.add_widget(Label(text="por Lucas Bonetti", font_size='10sp', color=(0.5, 0.5, 0.5, 1)))
        self.root.add_widget(topo)

        self.layout_feed = BoxLayout(orientation='vertical', size_hint_y=None, spacing=20)
        self.layout_feed.bind(minimum_height=self.layout_feed.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.layout_feed)
        self.root.add_widget(scroll)
        
        self.baixar_da_nuvem()
        return self.root

    def obter_id_celular(self):
        caminho_id = "meu_id.txt"
        if os.path.exists(caminho_id):
            with open(caminho_id, "r") as f: return f.read()
        novo_id = str(uuid.uuid4())
        with open(caminho_id, "w") as f: f.write(novo_id)
        return novo_id

    def baixar_da_nuvem(self, *args):
        threading.Thread(target=self.thread_baixar).start()

    def thread_baixar(self):
        try:
            res = requests.get(f"{LINK_BASE_FIREBASE}.json", timeout=10)
            dados = res.json() or {}
            Clock.schedule_once(lambda dt: self.atualizar_tela(dados))
        except: pass

    def atualizar_tela(self, dados):
        self.layout_feed.clear_widgets()
        ids = list(dados.keys())
        ids.reverse() 
        for id_fb in ids:
            if isinstance(dados[id_fb], dict):
                self.layout_feed.add_widget(Card(arvore=dados[id_fb], id_fb=id_fb, app_ref=self))

    def curtir_na_nuvem(self, id_fb, likes_atuais, ja_curtiu):
        if ja_curtiu: return
        threading.Thread(target=self.thread_like, args=(id_fb, likes_atuais)).start()

    def thread_like(self, id_fb, likes_atuais):
        try:
            url = f"{LINK_BASE_FIREBASE}/{id_fb}.json"
            payload = {"likes": likes_atuais + 1, f"curtidas_usuarios/{self.meu_id}": True}
            requests.patch(url, json=payload, timeout=10)
            Clock.schedule_once(lambda dt: self.baixar_da_nuvem())
        except: pass

    def abrir_painel(self, instance):
        conteudo = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.in_nome = TextInput(hint_text="Nome da Árvore", multiline=False)
        self.in_desc = TextInput(hint_text="Descrição (Max 100 letras)", multiline=False)
        self.btn_f = Button(text="ESCOLHER FOTO", background_color=(0.2, 0.4, 0.6, 1))
        self.btn_f.bind(on_press=self.abrir_seletor)
        self.btn_pub = Button(text="PUBLICAR", background_color=(0, 0.7, 0, 1), bold=True)
        self.btn_pub.bind(on_press=self.iniciar_upload)
        
        for w in [self.in_nome, self.in_desc, self.btn_f, self.btn_pub]: conteudo.add_widget(w)
        self.pop_add = Popup(title="Nova Postagem", content=conteudo, size_hint=(0.9, 0.8))
        self.pop_add.open()

    def iniciar_upload(self, instance):
        if not hasattr(self, 'sel') or not self.sel.selection:
            self.btn_pub.text = "FALTA FOTO"; return
        self.btn_pub.text = "ENVIANDO..."; self.btn_pub.disabled = True
        threading.Thread(target=self.upload_nuvem).start()

    def upload_nuvem(self):
        try:
            # Envio da foto com timeout maior para arquivos grandes
            with open(self.sel.selection[0], "rb") as f:
                res_img = requests.post("https://api.imgbb.com/1/upload", 
                                       data={"key": API_KEY_IMGBB, "image": base64.b64encode(f.read())}, timeout=60)
                url_foto = res_img.json()['data']['url']
            
            nova = {"nome": self.in_nome.text, "descricao": self.in_desc.text, "foto_url": url_foto, "likes": 0, "curtidas_usuarios": {}}
            requests.post(f"{LINK_BASE_FIREBASE}.json", json=nova, timeout=20)
            Clock.schedule_once(lambda dt: self.finalizar_upload())
        except:
            Clock.schedule_once(lambda dt: self.mostrar_erro_upload())

    def mostrar_erro_upload(self):
        self.btn_pub.text = "ERRO (NET LENTA?)"; self.btn_pub.disabled = False

    def finalizar_upload(self):
        self.pop_add.dismiss()
        self.baixar_da_nuvem()

    def abrir_seletor(self, instance):
        self.sel = FileChooserIconView(path='/sdcard')
        btn = Button(text="OK", size_hint_y=0.2)
        btn.bind(on_press=lambda x: self.pop_foto.dismiss())
        l = BoxLayout(orientation='vertical'); l.add_widget(self.sel); l.add_widget(btn)
        self.pop_foto = Popup(title="Galeria", content=l); self.pop_foto.open()

    def confirmar_exclusao(self, id_fb):
        btn = Button(text="CONFIRMAR EXCLUSÃO", background_color=(1,0,0,1))
        btn.bind(on_press=lambda x: self.excluir(id_fb))
        self.p_del = Popup(title="Apagar?", content=btn, size_hint=(0.8, 0.3))
        self.p_del.open()

    def excluir(self, id_fb):
        requests.delete(f"{LINK_BASE_FIREBASE}/{id_fb}.json")
        self.p_del.dismiss()
        self.baixar_da_nuvem()

    def compartilhar(self, arv):
        msg = f"🌲 *{arv['nome']}*\n{arv['descricao']}\n{arv['foto_url']}\n\nTreebook por Lucas Bonetti"
        Clipboard.copy(msg)
        p = Popup(title="Copiado!", content=Label(text="Link pronto para colar!"), size_hint=(0.8, 0.2))
        p.open()

if __name__ == '__main__':
    TreeBook().run()