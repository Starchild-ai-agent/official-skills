# Glossário pt-BR → 中文

巴西葡语术语对照表，用于阅读 Angulare / Tecnofit / NextFit 等巴西厂商的界面、
文档与 API 字段。**这是葡萄牙语（pt-BR），不是西班牙语。**

约定：之后遇到葡语原文，一律**给原文 + 中文翻译**，不做意译替换。

---

## 1. Angulare 后台导航（`dash.angulare.app`）

| 原文 | 中文 |
|---|---|
| Agendar | 预约 / 排课 |
| Vender | 销售（PDV 收银） |
| Dashboard | 仪表盘 |
| Clientes | 客户 |
| Vendas | 销售记录 |
| Financeiro | 财务 |
| Cadastros | 基础档案 |
| Relatórios | 报表 |
| Marketing | 营销 |
| Treinamentos | 训练 |
| Integrações | 集成 |
| **PDV** (Ponto de Venda) | 销售终端 / 收银台 |

## 2. 登录

| 原文 | 中文 |
|---|---|
| Senha | 密码 |
| Prosseguir | 继续 |
| Voltar | 返回 |
| Tenant escolhido | 已选租户 |
| Selecione o usuário | 选择用户 |
| Conectado em | 当前连接门店 |
| ALTERAR | 更改 |

## 3. PDV（Vender）三步流程

| 原文 | 中文 |
|---|---|
| Escolha a categoria | 选择分类 |
| Planos e produtos | 套餐与商品 |
| Adicionar | 添加 |
| Finalizar | 完成 / 结账 |
| Finalização da venda | 完成销售 |
| Mais categorias | 更多分类 |
| Cortesias | 赠品 / 免费额度 |
| Planos Avulsos | 单次套餐 |
| Eventos Especiais | 特别活动 |

## 4. 支付方式（PDV 付款步骤那一排方块）

| 原文 | 中文 |
|---|---|
| Cartão de crédito | 信用卡 |
| Cartão de débito | 借记卡 |
| Cartão de Crédito Presencial | 现场信用卡 |
| Cartão de Débito Presencial | 现场借记卡 |
| Dinheiro | 现金 |
| Pix | Pix（巴西即时支付） |
| Pix Presencial | 现场 Pix |
| Outro | 其他 |
| **Link de pagamento** | **付款链接** ← 就是这个按钮（代码里叫 `send-cart`） |

## 5. 卡片表单字段（客户在网页上看到的）

| 原文 | 中文 |
|---|---|
| Número do Cartão | 卡号 |
| CVV | 安全码 |
| Validade (MM/AAAA) | 有效期（月/年） |
| Nome do titular do cartão | 持卡人姓名 |
| Parcelamento / Parcelas | 分期 / 期数 |
| Pagamento à vista | 一次性付清（不分期） |
| Salvar dados para compras futuras | 保存卡信息以便下次购买 |
| Cartões de crédito cadastrados | 已保存的信用卡 |
| Preferencial | 首选卡 |
| Novo método de pagamento | 新增支付方式 |

## 6. 「Link de pagamento」弹出的对话框

| 原文 | 中文 |
|---|---|
| Enviar Carrinho (pagamento online) | 发送购物车（在线支付） |
| Escolha as opções de envio | 选择发送方式 |
| Expirar o link em | 链接过期时间 |
| Solicitar recadastramento | 要求重新登记资料 |
| Solicitar cadastro de novo cartão | 要求登记新卡 |
| Solicitar troca de senha | 要求修改密码 |
| Mostrar checkout como último passo | 把结账作为最后一步展示 |
| Enviar | 发送 |
| Envio de compartilhamento com sucesso | 分享发送成功 |

## 7. 错误信息（API / 界面）

| 原文 | 中文 | 说明 |
|---|---|---|
| Usuário ou senha inválido | 用户名或密码无效 | Basic 认证被拒 |
| **Login expirado!** | **登录已过期** | 实为用错 `Bearer`（应用 `JWT`） |
| Email não encontrado | 邮箱未找到 | 实为缺 `tenant` 头 |
| As credenciais de autenticação não foram fornecidas | 未提供认证凭证 | 完全未认证 |
| Cliente nao encontrado, verifique a URL | 未找到客户，请检查 URL | SSO 上租户不匹配 |
| No Event matches the given query | 没有匹配该查询的场次 | 对象级 404 |
| Chaves de API Open só podem ser usadas em URLs sob /api/open/ | 开放 API Key 只能用于 /api/open/ 下的 URL | 用错面 |
| Informe o header Tenant | 请提供 Tenant 头 | 开放 API 必需 |

## 8. 业务对象（预约 / 考勤 / 会员）

| 原文 | 中文 | 对应 API |
|---|---|---|
| Evento | 场次（一次开课） | `events/events/` |
| EventBook | 预约记录（报名） | `event-books/` |
| Atividade / Atividades | 课程 / 活动 | `events/activities/` |
| Agenda | 日程 / 课表 | `events/schedule/` |
| Reserva | 预约 | — |
| Check-in | 签到 | `checkedin_at` |
| Presença | 出勤 | — |
| Falta | 缺勤 | — |
| Falta justificada | 请假 | `justified_absence` |
| No-show | 未到场 | `noshow_at` |
| Matrícula / Matricular | 报名 / 注册 | `matrícula` |
| Aluno | 学员（会员） | — |
| Cliente | 客户 | `users/users/` |
| Créditos | 课时额度 | `credit-packages/` |
| Pacote de créditos | 课时包 | — |
| Lista de espera | 候补名单 | `waiting-list` |
| Unidade / Filial | 门店 / 分店 | `events/units/` |
| Rede / Franquia | 网络 / 加盟 | — |
| Plano | 套餐 | `products/products/` |
| Assinatura | 订阅 | `subscriptions/` |
| Contrato | 合约 | `membership` |
| Sala | 教室 | `events/rooms/` |
| Instrutor / Professor | 教练 | `events/instructors/` |

## 9. 状态值（`status` 字段）

| 原文 | 中文 |
|---|---|
| Pago | 已支付 |
| Pendente | 待支付 |
| Cancelado | 已取消 |
| Aguardando pagamento pix | 等待 Pix 支付 |
| checked-in | 已签到 |
| booked | 已预约 |
| waiting-list | 候补中 |
| canceled | 已取消 |
| late-canceled | 迟取消 |
| no-show | 未到场 |

## 10. 其他常见词

| 原文 | 中文 |
|---|---|
| Venda | 销售 |
| Cobrança | 收款 / 催收 |
| Recebível / Recebíveis | 应收 / 应收账款 |
| Nota fiscal (NF-e / NFS-e) | 电子发票（商品 / 服务） |
| Implantação | 实施（部署） |
| Homologação | 验收 / 上线前测试 |
| Chave de acesso | 访问密钥 |
| Termo de Adesão | 加入协议（签约文件） |
| Agregador | 聚合平台（Wellhub / TotalPass 这类） |
| Bem-vindo | 欢迎 |
| Bom dia | 早上好 |
