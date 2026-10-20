const vt = globalThis, Sn = vt.ShadowRoot && (vt.ShadyCSS === void 0 || vt.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, En = /* @__PURE__ */ Symbol(), ws = /* @__PURE__ */ new WeakMap();
let rr = class {
  constructor(e, t, r) {
    if (this._$cssResult$ = !0, r !== En) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (Sn && e === void 0) {
      const r = t !== void 0 && t.length === 1;
      r && (e = ws.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), r && ws.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const hi = (n) => new rr(typeof n == "string" ? n : n + "", void 0, En), di = (n, ...e) => {
  const t = n.length === 1 ? n[0] : e.reduce((r, s, a) => r + ((o) => {
    if (o._$cssResult$ === !0) return o.cssText;
    if (typeof o == "number") return o;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + o + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s) + n[a + 1], n[0]);
  return new rr(t, n, En);
}, fi = (n, e) => {
  if (Sn) n.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const r = document.createElement("style"), s = vt.litNonce;
    s !== void 0 && r.setAttribute("nonce", s), r.textContent = t.cssText, n.appendChild(r);
  }
}, As = Sn ? (n) => n : (n) => n instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const r of e.cssRules) t += r.cssText;
  return hi(t);
})(n) : n;
const { is: gi, defineProperty: mi, getOwnPropertyDescriptor: bi, getOwnPropertyNames: _i, getOwnPropertySymbols: yi, getPrototypeOf: xi } = Object, It = globalThis, vs = It.trustedTypes, ki = vs ? vs.emptyScript : "", wi = It.reactiveElementPolyfillSupport, it = (n, e) => n, $t = { toAttribute(n, e) {
  switch (e) {
    case Boolean:
      n = n ? ki : null;
      break;
    case Object:
    case Array:
      n = n == null ? n : JSON.stringify(n);
  }
  return n;
}, fromAttribute(n, e) {
  let t = n;
  switch (e) {
    case Boolean:
      t = n !== null;
      break;
    case Number:
      t = n === null ? null : Number(n);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(n);
      } catch {
        t = null;
      }
  }
  return t;
} }, Rn = (n, e) => !gi(n, e), $s = { attribute: !0, type: String, converter: $t, reflect: !1, useDefault: !1, hasChanged: Rn };
Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), It.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
let He = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ??= []).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = $s) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const r = /* @__PURE__ */ Symbol(), s = this.getPropertyDescriptor(e, r, t);
      s !== void 0 && mi(this.prototype, e, s);
    }
  }
  static getPropertyDescriptor(e, t, r) {
    const { get: s, set: a } = bi(this.prototype, e) ?? { get() {
      return this[t];
    }, set(o) {
      this[t] = o;
    } };
    return { get: s, set(o) {
      const u = s?.call(this);
      a?.call(this, o), this.requestUpdate(e, u, r);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? $s;
  }
  static _$Ei() {
    if (this.hasOwnProperty(it("elementProperties"))) return;
    const e = xi(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(it("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(it("properties"))) {
      const t = this.properties, r = [..._i(t), ...yi(t)];
      for (const s of r) this.createProperty(s, t[s]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [r, s] of t) this.elementProperties.set(r, s);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, r] of this.elementProperties) {
      const s = this._$Eu(t, r);
      s !== void 0 && this._$Eh.set(s, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const r = new Set(e.flat(1 / 0).reverse());
      for (const s of r) t.unshift(As(s));
    } else e !== void 0 && t.push(As(e));
    return t;
  }
  static _$Eu(e, t) {
    const r = t.attribute;
    return r === !1 ? void 0 : typeof r == "string" ? r : typeof e == "string" ? e.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
  }
  addController(e) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
  }
  removeController(e) {
    this._$EO?.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
    for (const r of t.keys()) this.hasOwnProperty(r) && (e.set(r, this[r]), delete this[r]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return fi(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    this._$EO?.forEach((e) => e.hostDisconnected?.());
  }
  attributeChangedCallback(e, t, r) {
    this._$AK(e, r);
  }
  _$ET(e, t) {
    const r = this.constructor.elementProperties.get(e), s = this.constructor._$Eu(e, r);
    if (s !== void 0 && r.reflect === !0) {
      const a = (r.converter?.toAttribute !== void 0 ? r.converter : $t).toAttribute(t, r.type);
      this._$Em = e, a == null ? this.removeAttribute(s) : this.setAttribute(s, a), this._$Em = null;
    }
  }
  _$AK(e, t) {
    const r = this.constructor, s = r._$Eh.get(e);
    if (s !== void 0 && this._$Em !== s) {
      const a = r.getPropertyOptions(s), o = typeof a.converter == "function" ? { fromAttribute: a.converter } : a.converter?.fromAttribute !== void 0 ? a.converter : $t;
      this._$Em = s;
      const u = o.fromAttribute(t, a.type);
      this[s] = u ?? this._$Ej?.get(s) ?? u, this._$Em = null;
    }
  }
  requestUpdate(e, t, r, s = !1, a) {
    if (e !== void 0) {
      const o = this.constructor;
      if (s === !1 && (a = this[e]), r ??= o.getPropertyOptions(e), !((r.hasChanged ?? Rn)(a, t) || r.useDefault && r.reflect && a === this._$Ej?.get(e) && !this.hasAttribute(o._$Eu(e, r)))) return;
      this.C(e, t, r);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: r, reflect: s, wrapped: a }, o) {
    r && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, o ?? t ?? this[e]), a !== !0 || o !== void 0) || (this._$AL.has(e) || (this.hasUpdated || r || (t = void 0), this._$AL.set(e, t)), s === !0 && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (t) {
      Promise.reject(t);
    }
    const e = this.scheduleUpdate();
    return e != null && await e, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [s, a] of this._$Ep) this[s] = a;
        this._$Ep = void 0;
      }
      const r = this.constructor.elementProperties;
      if (r.size > 0) for (const [s, a] of r) {
        const { wrapped: o } = a, u = this[s];
        o !== !0 || this._$AL.has(s) || u === void 0 || this.C(s, void 0, a, u);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((r) => r.hostUpdate?.()), this.update(t)) : this._$EM();
    } catch (r) {
      throw e = !1, this._$EM(), r;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    this._$EO?.forEach((t) => t.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(e) {
    return !0;
  }
  update(e) {
    this._$Eq &&= this._$Eq.forEach((t) => this._$ET(t, this[t])), this._$EM();
  }
  updated(e) {
  }
  firstUpdated(e) {
  }
};
He.elementStyles = [], He.shadowRootOptions = { mode: "open" }, He[it("elementProperties")] = /* @__PURE__ */ new Map(), He[it("finalized")] = /* @__PURE__ */ new Map(), wi?.({ ReactiveElement: He }), (It.reactiveElementVersions ??= []).push("2.1.2");
const In = globalThis, Ts = (n) => n, Tt = In.trustedTypes, Ss = Tt ? Tt.createPolicy("lit-html", { createHTML: (n) => n }) : void 0, ir = "$lit$", me = `lit$${Math.random().toFixed(9).slice(2)}$`, or = "?" + me, Ai = `<${or}>`, Se = document, lt = () => Se.createComment(""), ct = (n) => n === null || typeof n != "object" && typeof n != "function", On = Array.isArray, vi = (n) => On(n) || typeof n?.[Symbol.iterator] == "function", an = `[ 	
\f\r]`, Xe = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, Es = /-->/g, Rs = />/g, Ae = RegExp(`>|${an}(?:([^\\s"'>=/]+)(${an}*=${an}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), Is = /'/g, Os = /"/g, ar = /^(?:script|style|textarea|title)$/i, $i = (n) => (e, ...t) => ({ _$litType$: n, strings: e, values: t }), S = $i(1), be = /* @__PURE__ */ Symbol.for("lit-noChange"), $ = /* @__PURE__ */ Symbol.for("lit-nothing"), Cs = /* @__PURE__ */ new WeakMap(), Te = Se.createTreeWalker(Se, 129);
function lr(n, e) {
  if (!On(n) || !n.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return Ss !== void 0 ? Ss.createHTML(e) : e;
}
const Ti = (n, e) => {
  const t = n.length - 1, r = [];
  let s, a = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", o = Xe;
  for (let u = 0; u < t; u++) {
    const c = n[u];
    let m, g, f = -1, b = 0;
    for (; b < c.length && (o.lastIndex = b, g = o.exec(c), g !== null); ) b = o.lastIndex, o === Xe ? g[1] === "!--" ? o = Es : g[1] !== void 0 ? o = Rs : g[2] !== void 0 ? (ar.test(g[2]) && (s = RegExp("</" + g[2], "g")), o = Ae) : g[3] !== void 0 && (o = Ae) : o === Ae ? g[0] === ">" ? (o = s ?? Xe, f = -1) : g[1] === void 0 ? f = -2 : (f = o.lastIndex - g[2].length, m = g[1], o = g[3] === void 0 ? Ae : g[3] === '"' ? Os : Is) : o === Os || o === Is ? o = Ae : o === Es || o === Rs ? o = Xe : (o = Ae, s = void 0);
    const y = o === Ae && n[u + 1].startsWith("/>") ? " " : "";
    a += o === Xe ? c + Ai : f >= 0 ? (r.push(m), c.slice(0, f) + ir + c.slice(f) + me + y) : c + me + (f === -2 ? u : y);
  }
  return [lr(n, a + (n[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), r];
};
let xn = class cr {
  constructor({ strings: e, _$litType$: t }, r) {
    let s;
    this.parts = [];
    let a = 0, o = 0;
    const u = e.length - 1, c = this.parts, [m, g] = Ti(e, t);
    if (this.el = cr.createElement(m, r), Te.currentNode = this.el.content, t === 2 || t === 3) {
      const f = this.el.content.firstChild;
      f.replaceWith(...f.childNodes);
    }
    for (; (s = Te.nextNode()) !== null && c.length < u; ) {
      if (s.nodeType === 1) {
        if (s.hasAttributes()) for (const f of s.getAttributeNames()) if (f.endsWith(ir)) {
          const b = g[o++], y = s.getAttribute(f).split(me), k = /([.?@])?(.*)/.exec(b);
          c.push({ type: 1, index: a, name: k[2], strings: y, ctor: k[1] === "." ? Ei : k[1] === "?" ? Ri : k[1] === "@" ? Ii : Ct }), s.removeAttribute(f);
        } else f.startsWith(me) && (c.push({ type: 6, index: a }), s.removeAttribute(f));
        if (ar.test(s.tagName)) {
          const f = s.textContent.split(me), b = f.length - 1;
          if (b > 0) {
            s.textContent = Tt ? Tt.emptyScript : "";
            for (let y = 0; y < b; y++) s.append(f[y], lt()), Te.nextNode(), c.push({ type: 2, index: ++a });
            s.append(f[b], lt());
          }
        }
      } else if (s.nodeType === 8) if (s.data === or) c.push({ type: 2, index: a });
      else {
        let f = -1;
        for (; (f = s.data.indexOf(me, f + 1)) !== -1; ) c.push({ type: 7, index: a }), f += me.length - 1;
      }
      a++;
    }
  }
  static createElement(e, t) {
    const r = Se.createElement("template");
    return r.innerHTML = e, r;
  }
};
function We(n, e, t = n, r) {
  if (e === be) return e;
  let s = r !== void 0 ? t._$Co?.[r] : t._$Cl;
  const a = ct(e) ? void 0 : e._$litDirective$;
  return s?.constructor !== a && (s?._$AO?.(!1), a === void 0 ? s = void 0 : (s = new a(n), s._$AT(n, t, r)), r !== void 0 ? (t._$Co ??= [])[r] = s : t._$Cl = s), s !== void 0 && (e = We(n, s._$AS(n, e.values), s, r)), e;
}
class Si {
  constructor(e, t) {
    this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const { el: { content: t }, parts: r } = this._$AD, s = (e?.creationScope ?? Se).importNode(t, !0);
    Te.currentNode = s;
    let a = Te.nextNode(), o = 0, u = 0, c = r[0];
    for (; c !== void 0; ) {
      if (o === c.index) {
        let m;
        c.type === 2 ? m = new Ot(a, a.nextSibling, this, e) : c.type === 1 ? m = new c.ctor(a, c.name, c.strings, this, e) : c.type === 6 && (m = new Oi(a, this, e)), this._$AV.push(m), c = r[++u];
      }
      o !== c?.index && (a = Te.nextNode(), o++);
    }
    return Te.currentNode = Se, s;
  }
  p(e) {
    let t = 0;
    for (const r of this._$AV) r !== void 0 && (r.strings !== void 0 ? (r._$AI(e, r, t), t += r.strings.length - 2) : r._$AI(e[t])), t++;
  }
}
let Ot = class ur {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(e, t, r, s) {
    this.type = 2, this._$AH = $, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = r, this.options = s, this._$Cv = s?.isConnected ?? !0;
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const t = this._$AM;
    return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, t = this) {
    e = We(this, e, t), ct(e) ? e === $ || e == null || e === "" ? (this._$AH !== $ && this._$AR(), this._$AH = $) : e !== this._$AH && e !== be && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : vi(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== $ && ct(this._$AH) ? this._$AA.nextSibling.data = e : this.T(Se.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    const { values: t, _$litType$: r } = e, s = typeof r == "number" ? this._$AC(e) : (r.el === void 0 && (r.el = xn.createElement(lr(r.h, r.h[0]), this.options)), r);
    if (this._$AH?._$AD === s) this._$AH.p(t);
    else {
      const a = new Si(s, this), o = a.u(this.options);
      a.p(t), this.T(o), this._$AH = a;
    }
  }
  _$AC(e) {
    let t = Cs.get(e.strings);
    return t === void 0 && Cs.set(e.strings, t = new xn(e)), t;
  }
  k(e) {
    On(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let r, s = 0;
    for (const a of e) s === t.length ? t.push(r = new ur(this.O(lt()), this.O(lt()), this, this.options)) : r = t[s], r._$AI(a), s++;
    s < t.length && (this._$AR(r && r._$AB.nextSibling, s), t.length = s);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    for (this._$AP?.(!1, !0, t); e !== this._$AB; ) {
      const r = Ts(e).nextSibling;
      Ts(e).remove(), e = r;
    }
  }
  setConnected(e) {
    this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
  }
};
class Ct {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, r, s, a) {
    this.type = 1, this._$AH = $, this._$AN = void 0, this.element = e, this.name = t, this._$AM = s, this.options = a, r.length > 2 || r[0] !== "" || r[1] !== "" ? (this._$AH = Array(r.length - 1).fill(new String()), this.strings = r) : this._$AH = $;
  }
  _$AI(e, t = this, r, s) {
    const a = this.strings;
    let o = !1;
    if (a === void 0) e = We(this, e, t, 0), o = !ct(e) || e !== this._$AH && e !== be, o && (this._$AH = e);
    else {
      const u = e;
      let c, m;
      for (e = a[0], c = 0; c < a.length - 1; c++) m = We(this, u[r + c], t, c), m === be && (m = this._$AH[c]), o ||= !ct(m) || m !== this._$AH[c], m === $ ? e = $ : e !== $ && (e += (m ?? "") + a[c + 1]), this._$AH[c] = m;
    }
    o && !s && this.j(e);
  }
  j(e) {
    e === $ ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
let Ei = class extends Ct {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === $ ? void 0 : e;
  }
}, Ri = class extends Ct {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== $);
  }
}, Ii = class extends Ct {
  constructor(e, t, r, s, a) {
    super(e, t, r, s, a), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = We(this, e, t, 0) ?? $) === be) return;
    const r = this._$AH, s = e === $ && r !== $ || e.capture !== r.capture || e.once !== r.once || e.passive !== r.passive, a = e !== $ && (r === $ || s);
    s && this.element.removeEventListener(this.name, this, r), a && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
  }
};
class Oi {
  constructor(e, t, r) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = r;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    We(this, e);
  }
}
const Ci = { I: Ot }, Pi = In.litHtmlPolyfillSupport;
Pi?.(xn, Ot), (In.litHtmlVersions ??= []).push("3.3.3");
const Li = (n, e, t) => {
  const r = t?.renderBefore ?? e;
  let s = r._$litPart$;
  if (s === void 0) {
    const a = t?.renderBefore ?? null;
    r._$litPart$ = s = new Ot(e.insertBefore(lt(), a), a, void 0, t ?? {});
  }
  return s._$AI(n), s;
};
const Cn = globalThis;
let ot = class extends He {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const e = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= e.firstChild, e;
  }
  update(e) {
    const t = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Li(t, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(!0);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(!1);
  }
  render() {
    return be;
  }
};
ot._$litElement$ = !0, ot.finalized = !0, Cn.litElementHydrateSupport?.({ LitElement: ot });
const Di = Cn.litElementPolyfillSupport;
Di?.({ LitElement: ot });
(Cn.litElementVersions ??= []).push("4.2.2");
const Mi = { attribute: !0, type: String, converter: $t, reflect: !1, hasChanged: Rn }, Ni = (n = Mi, e, t) => {
  const { kind: r, metadata: s } = t;
  let a = globalThis.litPropertyMetadata.get(s);
  if (a === void 0 && globalThis.litPropertyMetadata.set(s, a = /* @__PURE__ */ new Map()), r === "setter" && ((n = Object.create(n)).wrapped = !0), a.set(t.name, n), r === "accessor") {
    const { name: o } = t;
    return { set(u) {
      const c = e.get.call(this);
      e.set.call(this, u), this.requestUpdate(o, c, n, !0, u);
    }, init(u) {
      return u !== void 0 && this.C(o, void 0, n, u), u;
    } };
  }
  if (r === "setter") {
    const { name: o } = t;
    return function(u) {
      const c = this[o];
      e.call(this, u), this.requestUpdate(o, c, n, !0, u);
    };
  }
  throw Error("Unsupported decorator location: " + r);
};
function Pn(n) {
  return (e, t) => typeof t == "object" ? Ni(n, e, t) : ((r, s, a) => {
    const o = s.hasOwnProperty(a);
    return s.constructor.createProperty(a, r), o ? Object.getOwnPropertyDescriptor(s, a) : void 0;
  })(n, e, t);
}
function te(n) {
  return Pn({ ...n, state: !0, attribute: !1 });
}
const zi = (n, e, t) => (t.configurable = !0, t.enumerable = !0, Reflect.decorate && typeof e != "object" && Object.defineProperty(n, e, t), t);
function pr(n, e) {
  return (t, r, s) => {
    const a = (o) => o.renderRoot?.querySelector(n) ?? null;
    return zi(t, r, { get() {
      return a(this);
    } });
  };
}
const hr = { CHILD: 2 }, dr = (n) => (...e) => ({ _$litDirective$: n, values: e });
let fr = class {
  constructor(e) {
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AT(e, t, r) {
    this._$Ct = e, this._$AM = t, this._$Ci = r;
  }
  _$AS(e, t) {
    return this.update(e, t);
  }
  update(e, t) {
    return this.render(...t);
  }
};
class kn extends fr {
  constructor(e) {
    if (super(e), this.it = $, e.type !== hr.CHILD) throw Error(this.constructor.directiveName + "() can only be used in child bindings");
  }
  render(e) {
    if (e === $ || e == null) return this._t = void 0, this.it = e;
    if (e === be) return e;
    if (typeof e != "string") throw Error(this.constructor.directiveName + "() called with a non-string value");
    if (e === this.it) return this._t;
    this.it = e;
    const t = [e];
    return t.raw = t, this._t = { _$litType$: this.constructor.resultType, strings: t, values: [] };
  }
}
kn.directiveName = "unsafeHTML", kn.resultType = 1;
const Ui = dr(kn);
const { I: Hi } = Ci, Ps = (n) => n, Ls = () => document.createComment(""), Ke = (n, e, t) => {
  const r = n._$AA.parentNode, s = e === void 0 ? n._$AB : e._$AA;
  if (t === void 0) {
    const a = r.insertBefore(Ls(), s), o = r.insertBefore(Ls(), s);
    t = new Hi(a, o, n, n.options);
  } else {
    const a = t._$AB.nextSibling, o = t._$AM, u = o !== n;
    if (u) {
      let c;
      t._$AQ?.(n), t._$AM = n, t._$AP !== void 0 && (c = n._$AU) !== o._$AU && t._$AP(c);
    }
    if (a !== s || u) {
      let c = t._$AA;
      for (; c !== a; ) {
        const m = Ps(c).nextSibling;
        Ps(r).insertBefore(c, s), c = m;
      }
    }
  }
  return t;
}, ve = (n, e, t = n) => (n._$AI(e, t), n), Bi = {}, Fi = (n, e = Bi) => n._$AH = e, Wi = (n) => n._$AH, ln = (n) => {
  n._$AR(), n._$AA.remove();
};
const Ds = (n, e, t) => {
  const r = /* @__PURE__ */ new Map();
  for (let s = e; s <= t; s++) r.set(n[s], s);
  return r;
}, ji = dr(class extends fr {
  constructor(n) {
    if (super(n), n.type !== hr.CHILD) throw Error("repeat() can only be used in text expressions");
  }
  dt(n, e, t) {
    let r;
    t === void 0 ? t = e : e !== void 0 && (r = e);
    const s = [], a = [];
    let o = 0;
    for (const u of n) s[o] = r ? r(u, o) : o, a[o] = t(u, o), o++;
    return { values: a, keys: s };
  }
  render(n, e, t) {
    return this.dt(n, e, t).values;
  }
  update(n, [e, t, r]) {
    const s = Wi(n), { values: a, keys: o } = this.dt(e, t, r);
    if (!Array.isArray(s)) return this.ut = o, a;
    const u = this.ut ??= [], c = [];
    let m, g, f = 0, b = s.length - 1, y = 0, k = a.length - 1;
    for (; f <= b && y <= k; ) if (s[f] === null) f++;
    else if (s[b] === null) b--;
    else if (u[f] === o[y]) c[y] = ve(s[f], a[y]), f++, y++;
    else if (u[b] === o[k]) c[k] = ve(s[b], a[k]), b--, k--;
    else if (u[f] === o[k]) c[k] = ve(s[f], a[k]), Ke(n, c[k + 1], s[f]), f++, k--;
    else if (u[b] === o[y]) c[y] = ve(s[b], a[y]), Ke(n, s[f], s[b]), b--, y++;
    else if (m === void 0 && (m = Ds(o, y, k), g = Ds(u, f, b)), m.has(u[f])) if (m.has(u[b])) {
      const R = g.get(o[y]), X = R !== void 0 ? s[R] : null;
      if (X === null) {
        const V = Ke(n, s[f]);
        ve(V, a[y]), c[y] = V;
      } else c[y] = ve(X, a[y]), Ke(n, s[f], X), s[R] = null;
      y++;
    } else ln(s[b]), b--;
    else ln(s[f]), f++;
    for (; y <= k; ) {
      const R = Ke(n, c[k + 1]);
      ve(R, a[y]), c[y++] = R;
    }
    for (; f <= b; ) {
      const R = s[f++];
      R !== null && ln(R);
    }
    return this.ut = o, Fi(n, c), be;
  }
});
function Ms(n, e) {
  (e == null || e > n.length) && (e = n.length);
  for (var t = 0, r = Array(e); t < e; t++) r[t] = n[t];
  return r;
}
function Gi(n) {
  if (Array.isArray(n)) return n;
}
function qi(n, e) {
  var t = n == null ? null : typeof Symbol < "u" && n[Symbol.iterator] || n["@@iterator"];
  if (t != null) {
    var r, s, a, o, u = [], c = !0, m = !1;
    try {
      if (a = (t = t.call(n)).next, e !== 0) for (; !(c = (r = a.call(t)).done) && (u.push(r.value), u.length !== e); c = !0) ;
    } catch (g) {
      m = !0, s = g;
    } finally {
      try {
        if (!c && t.return != null && (o = t.return(), Object(o) !== o)) return;
      } finally {
        if (m) throw s;
      }
    }
    return u;
  }
}
function Yi() {
  throw new TypeError(`Invalid attempt to destructure non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`);
}
function Vi(n, e) {
  return Gi(n) || qi(n, e) || Zi(n, e) || Yi();
}
function Zi(n, e) {
  if (n) {
    if (typeof n == "string") return Ms(n, e);
    var t = {}.toString.call(n).slice(8, -1);
    return t === "Object" && n.constructor && (t = n.constructor.name), t === "Map" || t === "Set" ? Array.from(n) : t === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? Ms(n, e) : void 0;
  }
}
const gr = Object.entries, Ns = Object.setPrototypeOf, Xi = Object.isFrozen, mr = Object.getPrototypeOf, br = Object.getOwnPropertyDescriptor;
let N = Object.freeze, U = Object.seal, Be = Object.create, _r = typeof Reflect < "u" && Reflect, wn = _r.apply, An = _r.construct;
N || (N = function(e) {
  return e;
});
U || (U = function(e) {
  return e;
});
wn || (wn = function(e, t) {
  for (var r = arguments.length, s = new Array(r > 2 ? r - 2 : 0), a = 2; a < r; a++) s[a - 2] = arguments[a];
  return e.apply(t, s);
});
An || (An = function(e) {
  for (var t = arguments.length, r = new Array(t > 1 ? t - 1 : 0), s = 1; s < t; s++) r[s - 1] = arguments[s];
  return new e(...r);
});
const le = C(Array.prototype.forEach), Ki = C(Array.prototype.lastIndexOf), zs = C(Array.prototype.pop), Qe = C(Array.prototype.push), Qi = C(Array.prototype.slice), Ji = C(Array.prototype.splice), Fe = Array.isArray, cn = yr(Set), un = C(Set.prototype.add), Je = C(Set.prototype.has), $e = C(String.prototype.toLowerCase), pn = C(String.prototype.toString), Us = C(String.prototype.match), et = C(String.prototype.replace), Hs = C(String.prototype.indexOf), eo = C(String.prototype.trim), to = C(Number.prototype.toString), no = C(Boolean.prototype.toString), Bs = typeof BigInt > "u" ? null : C(BigInt.prototype.toString), Fs = typeof Symbol > "u" ? null : C(Symbol.prototype.toString), Y = C(Object.prototype.hasOwnProperty), tt = C(Object.prototype.toString), z = C(RegExp.prototype.test), ce = yr(TypeError);
function C(n) {
  return function(e) {
    e instanceof RegExp && (e.lastIndex = 0);
    for (var t = arguments.length, r = new Array(t > 1 ? t - 1 : 0), s = 1; s < t; s++) r[s - 1] = arguments[s];
    return wn(n, e, r);
  };
}
function yr(n) {
  return function() {
    for (var e = arguments.length, t = new Array(e), r = 0; r < e; r++) t[r] = arguments[r];
    return An(n, t);
  };
}
function A(n, e) {
  let t = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : $e;
  if (Ns && Ns(n, null), !Fe(e)) return n;
  let r = e.length;
  for (; r--; ) {
    let s = e[r];
    if (typeof s == "string") {
      const a = t(s);
      a !== s && (Xi(e) || (e[r] = a), s = a);
    }
    n[s] = !0;
  }
  return n;
}
function so(n) {
  for (let e = 0; e < n.length; e++) Y(n, e) || (n[e] = null);
  return n;
}
function Z(n) {
  const e = Be(null);
  for (const r of gr(n)) {
    var t = Vi(r, 2);
    const s = t[0], a = t[1];
    Y(n, s) && (Fe(a) ? e[s] = so(a) : a && typeof a == "object" && a.constructor === Object ? e[s] = Z(a) : e[s] = a);
  }
  return e;
}
function ro(n) {
  switch (typeof n) {
    case "string":
      return n;
    case "number":
      return to(n);
    case "boolean":
      return no(n);
    case "bigint":
      return Bs ? Bs(n) : "0";
    case "symbol":
      return Fs ? Fs(n) : "Symbol()";
    case "undefined":
      return tt(n);
    case "function":
    case "object": {
      if (n === null) return tt(n);
      const e = n, t = K(e, "toString");
      if (typeof t == "function") {
        const r = t(e);
        return typeof r == "string" ? r : tt(r);
      }
      return tt(n);
    }
    default:
      return tt(n);
  }
}
function K(n, e) {
  for (; n !== null; ) {
    const r = br(n, e);
    if (r) {
      if (r.get) return C(r.get);
      if (typeof r.value == "function") return C(r.value);
    }
    n = mr(n);
  }
  function t() {
    return null;
  }
  return t;
}
function io(n, e) {
  for (; n !== null; ) {
    const t = br(n, e);
    if (t) return t.get ? C(t.get) : null;
    n = mr(n);
  }
  return null;
}
function oo(n) {
  try {
    return z(n, ""), !0;
  } catch {
    return !1;
  }
}
const Ws = N([
  "a",
  "abbr",
  "acronym",
  "address",
  "area",
  "article",
  "aside",
  "audio",
  "b",
  "bdi",
  "bdo",
  "big",
  "blink",
  "blockquote",
  "body",
  "br",
  "button",
  "canvas",
  "caption",
  "center",
  "cite",
  "code",
  "col",
  "colgroup",
  "content",
  "data",
  "datalist",
  "dd",
  "decorator",
  "del",
  "details",
  "dfn",
  "dialog",
  "dir",
  "div",
  "dl",
  "dt",
  "element",
  "em",
  "fieldset",
  "figcaption",
  "figure",
  "font",
  "footer",
  "form",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "head",
  "header",
  "hgroup",
  "hr",
  "html",
  "i",
  "img",
  "input",
  "ins",
  "kbd",
  "label",
  "legend",
  "li",
  "main",
  "map",
  "mark",
  "marquee",
  "menu",
  "menuitem",
  "meter",
  "nav",
  "nobr",
  "ol",
  "optgroup",
  "option",
  "output",
  "p",
  "picture",
  "pre",
  "progress",
  "q",
  "rp",
  "rt",
  "ruby",
  "s",
  "samp",
  "search",
  "section",
  "select",
  "shadow",
  "slot",
  "small",
  "source",
  "spacer",
  "span",
  "strike",
  "strong",
  "style",
  "sub",
  "summary",
  "sup",
  "table",
  "tbody",
  "td",
  "template",
  "textarea",
  "tfoot",
  "th",
  "thead",
  "time",
  "tr",
  "track",
  "tt",
  "u",
  "ul",
  "var",
  "video",
  "wbr"
]), hn = N([
  "svg",
  "a",
  "altglyph",
  "altglyphdef",
  "altglyphitem",
  "animatecolor",
  "animatemotion",
  "animatetransform",
  "circle",
  "clippath",
  "defs",
  "desc",
  "ellipse",
  "enterkeyhint",
  "exportparts",
  "filter",
  "font",
  "g",
  "glyph",
  "glyphref",
  "hkern",
  "image",
  "inputmode",
  "line",
  "lineargradient",
  "marker",
  "mask",
  "metadata",
  "mpath",
  "part",
  "path",
  "pattern",
  "polygon",
  "polyline",
  "radialgradient",
  "rect",
  "stop",
  "style",
  "switch",
  "symbol",
  "text",
  "textpath",
  "title",
  "tref",
  "tspan",
  "view",
  "vkern"
]), dn = N([
  "feBlend",
  "feColorMatrix",
  "feComponentTransfer",
  "feComposite",
  "feConvolveMatrix",
  "feDiffuseLighting",
  "feDisplacementMap",
  "feDistantLight",
  "feDropShadow",
  "feFlood",
  "feFuncA",
  "feFuncB",
  "feFuncG",
  "feFuncR",
  "feGaussianBlur",
  "feImage",
  "feMerge",
  "feMergeNode",
  "feMorphology",
  "feOffset",
  "fePointLight",
  "feSpecularLighting",
  "feSpotLight",
  "feTile",
  "feTurbulence"
]), ao = N([
  "animate",
  "color-profile",
  "cursor",
  "discard",
  "font-face",
  "font-face-format",
  "font-face-name",
  "font-face-src",
  "font-face-uri",
  "foreignobject",
  "hatch",
  "hatchpath",
  "mesh",
  "meshgradient",
  "meshpatch",
  "meshrow",
  "missing-glyph",
  "script",
  "set",
  "solidcolor",
  "unknown",
  "use"
]), fn = N([
  "math",
  "menclose",
  "merror",
  "mfenced",
  "mfrac",
  "mglyph",
  "mi",
  "mlabeledtr",
  "mmultiscripts",
  "mn",
  "mo",
  "mover",
  "mpadded",
  "mphantom",
  "mroot",
  "mrow",
  "ms",
  "mspace",
  "msqrt",
  "mstyle",
  "msub",
  "msup",
  "msubsup",
  "mtable",
  "mtd",
  "mtext",
  "mtr",
  "munder",
  "munderover",
  "mprescripts"
]), lo = N([
  "maction",
  "maligngroup",
  "malignmark",
  "mlongdiv",
  "mscarries",
  "mscarry",
  "msgroup",
  "mstack",
  "msline",
  "msrow",
  "semantics",
  "annotation",
  "annotation-xml",
  "mprescripts",
  "none"
]), js = N(["#text"]), Gs = N([
  "accept",
  "action",
  "align",
  "alt",
  "autocapitalize",
  "autocomplete",
  "autopictureinpicture",
  "autoplay",
  "background",
  "bgcolor",
  "border",
  "capture",
  "cellpadding",
  "cellspacing",
  "checked",
  "cite",
  "class",
  "clear",
  "color",
  "cols",
  "colspan",
  "command",
  "commandfor",
  "controls",
  "controlslist",
  "coords",
  "crossorigin",
  "datetime",
  "decoding",
  "default",
  "dir",
  "disabled",
  "disablepictureinpicture",
  "disableremoteplayback",
  "download",
  "draggable",
  "enctype",
  "enterkeyhint",
  "exportparts",
  "face",
  "for",
  "headers",
  "height",
  "hidden",
  "high",
  "href",
  "hreflang",
  "id",
  "inert",
  "inputmode",
  "integrity",
  "ismap",
  "kind",
  "label",
  "lang",
  "list",
  "loading",
  "loop",
  "low",
  "max",
  "maxlength",
  "media",
  "method",
  "min",
  "minlength",
  "multiple",
  "muted",
  "name",
  "nonce",
  "noshade",
  "novalidate",
  "nowrap",
  "open",
  "optimum",
  "part",
  "pattern",
  "placeholder",
  "playsinline",
  "popover",
  "popovertarget",
  "popovertargetaction",
  "poster",
  "preload",
  "pubdate",
  "radiogroup",
  "readonly",
  "rel",
  "required",
  "rev",
  "reversed",
  "role",
  "rows",
  "rowspan",
  "spellcheck",
  "scope",
  "selected",
  "shape",
  "size",
  "sizes",
  "slot",
  "span",
  "srclang",
  "start",
  "src",
  "srcset",
  "step",
  "style",
  "summary",
  "tabindex",
  "title",
  "translate",
  "type",
  "usemap",
  "valign",
  "value",
  "width",
  "wrap",
  "xmlns"
]), gn = N([
  "accent-height",
  "accumulate",
  "additive",
  "alignment-baseline",
  "amplitude",
  "ascent",
  "attributename",
  "attributetype",
  "azimuth",
  "basefrequency",
  "baseline-shift",
  "begin",
  "bias",
  "by",
  "class",
  "clip",
  "clippathunits",
  "clip-path",
  "clip-rule",
  "color",
  "color-interpolation",
  "color-interpolation-filters",
  "color-profile",
  "color-rendering",
  "cx",
  "cy",
  "d",
  "dx",
  "dy",
  "diffuseconstant",
  "direction",
  "display",
  "divisor",
  "dominant-baseline",
  "dur",
  "edgemode",
  "elevation",
  "end",
  "exponent",
  "fill",
  "fill-opacity",
  "fill-rule",
  "filter",
  "filterunits",
  "flood-color",
  "flood-opacity",
  "font-family",
  "font-size",
  "font-size-adjust",
  "font-stretch",
  "font-style",
  "font-variant",
  "font-weight",
  "fx",
  "fy",
  "g1",
  "g2",
  "glyph-name",
  "glyphref",
  "gradientunits",
  "gradienttransform",
  "height",
  "href",
  "id",
  "image-rendering",
  "in",
  "in2",
  "intercept",
  "k",
  "k1",
  "k2",
  "k3",
  "k4",
  "kerning",
  "keypoints",
  "keysplines",
  "keytimes",
  "lang",
  "lengthadjust",
  "letter-spacing",
  "kernelmatrix",
  "kernelunitlength",
  "lighting-color",
  "local",
  "marker-end",
  "marker-mid",
  "marker-start",
  "markerheight",
  "markerunits",
  "markerwidth",
  "maskcontentunits",
  "maskunits",
  "max",
  "mask",
  "mask-type",
  "media",
  "method",
  "mode",
  "min",
  "name",
  "numoctaves",
  "offset",
  "operator",
  "opacity",
  "order",
  "orient",
  "orientation",
  "origin",
  "overflow",
  "paint-order",
  "path",
  "pathlength",
  "patterncontentunits",
  "patterntransform",
  "patternunits",
  "pointer-events",
  "points",
  "preservealpha",
  "preserveaspectratio",
  "primitiveunits",
  "r",
  "rx",
  "ry",
  "radius",
  "refx",
  "refy",
  "repeatcount",
  "repeatdur",
  "restart",
  "result",
  "rotate",
  "scale",
  "seed",
  "shape-rendering",
  "slope",
  "specularconstant",
  "specularexponent",
  "spreadmethod",
  "startoffset",
  "stddeviation",
  "stitchtiles",
  "stop-color",
  "stop-opacity",
  "stroke-dasharray",
  "stroke-dashoffset",
  "stroke-linecap",
  "stroke-linejoin",
  "stroke-miterlimit",
  "stroke-opacity",
  "stroke",
  "stroke-width",
  "style",
  "surfacescale",
  "systemlanguage",
  "tabindex",
  "tablevalues",
  "targetx",
  "targety",
  "transform",
  "transform-origin",
  "text-anchor",
  "text-decoration",
  "text-orientation",
  "text-rendering",
  "textlength",
  "type",
  "u1",
  "u2",
  "unicode",
  "values",
  "vector-effect",
  "viewbox",
  "visibility",
  "version",
  "vert-adv-y",
  "vert-origin-x",
  "vert-origin-y",
  "width",
  "word-spacing",
  "wrap",
  "writing-mode",
  "xchannelselector",
  "ychannelselector",
  "x",
  "x1",
  "x2",
  "xmlns",
  "y",
  "y1",
  "y2",
  "z",
  "zoomandpan"
]), qs = N([
  "accent",
  "accentunder",
  "align",
  "bevelled",
  "close",
  "columnalign",
  "columnlines",
  "columnspacing",
  "columnspan",
  "denomalign",
  "depth",
  "dir",
  "display",
  "displaystyle",
  "encoding",
  "fence",
  "frame",
  "height",
  "href",
  "id",
  "largeop",
  "length",
  "linethickness",
  "lquote",
  "lspace",
  "mathbackground",
  "mathcolor",
  "mathsize",
  "mathvariant",
  "maxsize",
  "minsize",
  "movablelimits",
  "notation",
  "numalign",
  "open",
  "rowalign",
  "rowlines",
  "rowspacing",
  "rowspan",
  "rspace",
  "rquote",
  "scriptlevel",
  "scriptminsize",
  "scriptsizemultiplier",
  "selection",
  "separator",
  "separators",
  "stretchy",
  "subscriptshift",
  "supscriptshift",
  "symmetric",
  "voffset",
  "width",
  "xmlns"
]), kt = N([
  "xlink:href",
  "xml:id",
  "xlink:title",
  "xml:space",
  "xmlns:xlink"
]), co = U(/{{[\w\W]*|^[\w\W]*}}/g), uo = U(/<%[\w\W]*|^[\w\W]*%>/g), po = U(/\${[\w\W]*/g), ho = U(/^data-[\-\w.\u00B7-\uFFFF]+$/), fo = U(/^aria-[\-\w]+$/), Ys = U(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i), go = U(/^(?:\w+script|data):/i), mo = U(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g), bo = U(/^html$/i), _o = U(/^[a-z][.\w]*(-[.\w]+)+$/i), mn = U(/<[/\w!]/g), Vs = U(/<[/\w]/g), yo = U(/<\/no(script|embed|frames)/i), Zs = U(/\/>/i), L = {
  element: 1,
  attribute: 2,
  text: 3,
  cdataSection: 4,
  entityReference: 5,
  entityNode: 6,
  processingInstruction: 7,
  comment: 8,
  document: 9,
  documentType: 10,
  documentFragment: 11,
  notation: 12
}, xo = N(A({}, [
  "style",
  "script",
  "xmp",
  "iframe",
  "noembed",
  "noframes",
  "plaintext",
  "noscript"
])), ko = function() {
  return typeof window > "u" ? null : window;
}, wo = function(e, t) {
  if (typeof e != "object" || typeof e.createPolicy != "function") return null;
  let r = null;
  const s = "data-tt-policy-suffix";
  t && t.hasAttribute(s) && (r = t.getAttribute(s));
  const a = "dompurify" + (r ? "#" + r : "");
  try {
    return e.createPolicy(a, {
      createHTML(o) {
        return o;
      },
      createScriptURL(o) {
        return o;
      }
    });
  } catch {
    return console.warn("TrustedTypes policy " + a + " could not be created."), null;
  }
}, Xs = function() {
  return {
    afterSanitizeAttributes: [],
    afterSanitizeElements: [],
    afterSanitizeShadowDOM: [],
    beforeSanitizeAttributes: [],
    beforeSanitizeElements: [],
    beforeSanitizeShadowDOM: [],
    uponSanitizeAttribute: [],
    uponSanitizeElement: [],
    uponSanitizeShadowNode: []
  };
}, ge = function(e, t, r, s) {
  return Y(e, t) && Fe(e[t]) ? A(s.base ? Z(s.base) : {}, e[t], s.transform) : r;
}, bn = function(e, t, r) {
  const s = Y(e, t) ? e[t] : void 0;
  return s && typeof s == "object" ? Z(s) : r();
};
function xr() {
  let n = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : ko();
  const e = (d) => xr(d);
  if (e.version = "3.4.17", e.removed = [], !n || !n.document || n.document.nodeType !== L.document || !n.Element)
    return e.isSupported = !1, e;
  let t = n.document;
  const r = t, s = r.currentScript;
  n.DocumentFragment;
  const a = n.HTMLTemplateElement, o = n.Node, u = n.Element, c = n.NodeFilter;
  n.NamedNodeMap === void 0 && (n.NamedNodeMap || n.MozNamedAttrMap), n.HTMLFormElement;
  const m = n.DOMParser, g = n.trustedTypes, f = u.prototype, b = K(f, "cloneNode"), y = K(f, "remove"), k = K(f, "removeAttributeNode"), R = K(f, "nextSibling"), X = K(f, "childNodes"), V = K(f, "parentNode"), Ie = K(f, "shadowRoot"), Oe = K(f, "attributes"), ne = o && o.prototype ? K(o.prototype, "nodeType") : null, ue = o && o.prototype ? K(o.prototype, "nodeName") : null, pe = o && o.prototype ? K(o.prototype, "ownerDocument") : null, M = function(i) {
    return ne ? ne(i) : i.nodeType;
  }, je = function(i) {
    return ue ? ue(i) : i.nodeName;
  }, Wn = io(f, "namespaceURI"), Dt = function(i) {
    return Wn ? Wn(i) : i.namespaceURI;
  };
  if (typeof a == "function") {
    const d = t.createElement("template");
    d.content && d.content.ownerDocument && (t = d.content.ownerDocument);
  }
  let j, _e = "", Mt, jn = !1, Ge = 0;
  const Gn = function() {
    if (Ge > 0) throw ce('A configured TRUSTED_TYPES_POLICY callback (createHTML or createScriptURL) must not call DOMPurify.sanitize, as that causes infinite recursion. Do not pass a policy whose callbacks wrap DOMPurify as TRUSTED_TYPES_POLICY; see the "DOMPurify and Trusted Types" section of the README.');
  }, Ce = function(i) {
    Gn(), Ge++;
    try {
      return j.createHTML(i);
    } finally {
      Ge--;
    }
  }, Lr = function(i) {
    Gn(), Ge++;
    try {
      return j.createScriptURL(i);
    } finally {
      Ge--;
    }
  }, Dr = function() {
    return jn || (Mt = wo(g, s), jn = !0), Mt;
  }, pt = t, Nt = pt.implementation, qn = pt.createNodeIterator, Mr = pt.createDocumentFragment, Nr = pt.getElementsByTagName, zr = r.importNode;
  let E = Xs();
  e.isSupported = typeof gr == "function" && typeof V == "function" && Nt && Nt.createHTMLDocument !== void 0;
  const Ur = co, Hr = uo, Br = po, Fr = ho, Wr = fo, jr = go, Yn = mo, Gr = _o;
  let Vn = Ys, I = null;
  const zt = A({}, [
    ...Ws,
    ...hn,
    ...dn,
    ...fn,
    ...js
  ]);
  let O = null;
  const Ut = A({}, [
    ...Gs,
    ...gn,
    ...qs,
    ...kt
  ]);
  let se = Object.seal(Be(null, {
    tagNameCheck: {
      writable: !0,
      configurable: !1,
      enumerable: !0,
      value: null
    },
    attributeNameCheck: {
      writable: !0,
      configurable: !1,
      enumerable: !0,
      value: null
    },
    allowCustomizedBuiltInElements: {
      writable: !0,
      configurable: !1,
      enumerable: !0,
      value: !1
    }
  })), qe = null, Zn = null;
  const he = Object.seal(Be(null, {
    tagCheck: {
      writable: !0,
      configurable: !1,
      enumerable: !0,
      value: null
    },
    attributeCheck: {
      writable: !0,
      configurable: !1,
      enumerable: !0,
      value: null
    }
  }));
  let Xn = !0, Ht = !0, Kn = !1, Bt = !0, ae = !1, ye = !0, xe = !1, Ft = !1, ht = null, dt = null, Wt = !1, Pe = !1, ft = !1, gt = !1, Qn = !0, Jn = !1;
  const es = "user-content-";
  let jt = !0, Gt = !1, ke = null, Le = {}, we = null;
  const ts = A({}, [
    "annotation-xml",
    "audio",
    "colgroup",
    "desc",
    "foreignobject",
    "head",
    "iframe",
    "math",
    "mi",
    "mn",
    "mo",
    "ms",
    "mtext",
    "noembed",
    "noframes",
    "noscript",
    "plaintext",
    "script",
    "selectedcontent",
    "style",
    "svg",
    "template",
    "thead",
    "title",
    "video",
    "xmp"
  ]);
  let ns = null;
  const ss = A({}, [
    "audio",
    "video",
    "img",
    "source",
    "image",
    "track"
  ]);
  let rs = null;
  const is = A({}, [
    "alt",
    "class",
    "for",
    "id",
    "label",
    "name",
    "pattern",
    "placeholder",
    "role",
    "summary",
    "title",
    "value",
    "style",
    "xmlns"
  ]), mt = "http://www.w3.org/1998/Math/MathML", bt = "http://www.w3.org/2000/svg", re = "http://www.w3.org/1999/xhtml";
  let De = re, qt = !1, Yt = null;
  const qr = A({}, [
    mt,
    bt,
    re
  ], pn), os = N([
    "mi",
    "mo",
    "mn",
    "ms",
    "mtext"
  ]);
  let Vt = A({}, os);
  const as = N(["annotation-xml"]);
  let Zt = A({}, as);
  const Yr = A({}, [
    "title",
    "style",
    "font",
    "a",
    "script"
  ]);
  let Ye = null;
  const Vr = ["application/xhtml+xml", "text/html"], Zr = "text/html";
  let P = null, Me = null;
  const Xr = t.createElement("form"), ls = function(i) {
    return i instanceof RegExp || i instanceof Function;
  }, Xt = function() {
    let i = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
    if (Me && Me === i) return;
    (!i || typeof i != "object") && (i = {}), i = Z(i), Ye = Vr.indexOf(i.PARSER_MEDIA_TYPE) === -1 ? Zr : i.PARSER_MEDIA_TYPE, P = Ye === "application/xhtml+xml" ? pn : $e, I = ge(i, "ALLOWED_TAGS", zt, { transform: P }), O = ge(i, "ALLOWED_ATTR", Ut, { transform: P }), Yt = ge(i, "ALLOWED_NAMESPACES", qr, { transform: pn }), rs = ge(i, "ADD_URI_SAFE_ATTR", is, {
      transform: P,
      base: is
    }), ns = ge(i, "ADD_DATA_URI_TAGS", ss, {
      transform: P,
      base: ss
    }), we = ge(i, "FORBID_CONTENTS", ts, { transform: P }), qe = ge(i, "FORBID_TAGS", Z({}), { transform: P }), Zn = ge(i, "FORBID_ATTR", Z({}), { transform: P }), Le = Y(i, "USE_PROFILES") ? i.USE_PROFILES && typeof i.USE_PROFILES == "object" ? Z(i.USE_PROFILES) : i.USE_PROFILES : !1, Xn = i.ALLOW_ARIA_ATTR !== !1, Ht = i.ALLOW_DATA_ATTR !== !1, Kn = i.ALLOW_UNKNOWN_PROTOCOLS || !1, Bt = i.ALLOW_SELF_CLOSE_IN_ATTR !== !1, ae = i.SAFE_FOR_TEMPLATES || !1, ye = i.SAFE_FOR_XML !== !1, xe = i.WHOLE_DOCUMENT || !1, Pe = i.RETURN_DOM || !1, ft = i.RETURN_DOM_FRAGMENT || !1, gt = i.RETURN_TRUSTED_TYPE || !1, Wt = i.FORCE_BODY || !1, Qn = i.SANITIZE_DOM !== !1, Jn = i.SANITIZE_NAMED_PROPS || !1, jt = i.KEEP_CONTENT !== !1, Gt = i.IN_PLACE || !1, Vn = oo(i.ALLOWED_URI_REGEXP) ? i.ALLOWED_URI_REGEXP : Ys, De = typeof i.NAMESPACE == "string" ? i.NAMESPACE : re, Vt = bn(i, "MATHML_TEXT_INTEGRATION_POINTS", () => A({}, os)), Zt = bn(i, "HTML_INTEGRATION_POINTS", () => A({}, as));
    const l = bn(i, "CUSTOM_ELEMENT_HANDLING", () => Be(null));
    if (se = Be(null), Y(l, "tagNameCheck") && ls(l.tagNameCheck) && (se.tagNameCheck = l.tagNameCheck), Y(l, "attributeNameCheck") && ls(l.attributeNameCheck) && (se.attributeNameCheck = l.attributeNameCheck), Y(l, "allowCustomizedBuiltInElements") && typeof l.allowCustomizedBuiltInElements == "boolean" && (se.allowCustomizedBuiltInElements = l.allowCustomizedBuiltInElements), U(se), ae && (Ht = !1), ft && (Pe = !0), Le && (I = A({}, js), O = Be(null), Le.html === !0 && (A(I, Ws), A(O, Gs)), Le.svg === !0 && (A(I, hn), A(O, gn), A(O, kt)), Le.svgFilters === !0 && (A(I, dn), A(O, gn), A(O, kt)), Le.mathMl === !0 && (A(I, fn), A(O, qs), A(O, kt))), he.tagCheck = null, he.attributeCheck = null, Y(i, "ADD_TAGS") && (typeof i.ADD_TAGS == "function" ? he.tagCheck = i.ADD_TAGS : Fe(i.ADD_TAGS) && (I === zt && (I = Z(I)), A(I, i.ADD_TAGS, P))), Y(i, "ADD_ATTR") && (typeof i.ADD_ATTR == "function" ? he.attributeCheck = i.ADD_ATTR : Fe(i.ADD_ATTR) && (O === Ut && (O = Z(O)), A(O, i.ADD_ATTR, P))), Y(i, "ADD_FORBID_CONTENTS") && Fe(i.ADD_FORBID_CONTENTS) && (we === ts && (we = Z(we)), A(we, i.ADD_FORBID_CONTENTS, P)), jt && (I["#text"] = !0), xe && A(I, [
      "html",
      "head",
      "body"
    ]), I.table && (A(I, ["tbody"]), delete qe.tbody), i.TRUSTED_TYPES_POLICY) {
      if (typeof i.TRUSTED_TYPES_POLICY.createHTML != "function") throw ce('TRUSTED_TYPES_POLICY configuration option must provide a "createHTML" hook.');
      if (typeof i.TRUSTED_TYPES_POLICY.createScriptURL != "function") throw ce('TRUSTED_TYPES_POLICY configuration option must provide a "createScriptURL" hook.');
      const p = j;
      j = i.TRUSTED_TYPES_POLICY;
      try {
        _e = Ce("");
      } catch (h) {
        throw j = p, h;
      }
    } else i.TRUSTED_TYPES_POLICY === null ? (j = void 0, _e = "") : (j === void 0 && (j = Dr()), j && typeof _e == "string" && (_e = Ce("")));
    N && N(i), Me = i;
  }, cs = A({}, [
    ...hn,
    ...dn,
    ...ao
  ]), us = A({}, [...fn, ...lo]), Kr = function(i, l, p) {
    return l.namespaceURI === re ? i === "svg" : l.namespaceURI === mt ? i === "svg" && (p === "annotation-xml" || Vt[p]) : !!cs[i];
  }, Qr = function(i, l, p) {
    return l.namespaceURI === re ? i === "math" : l.namespaceURI === bt ? i === "math" && Zt[p] : !!us[i];
  }, Jr = function(i, l, p) {
    return l.namespaceURI === bt && !Zt[p] || l.namespaceURI === mt && !Vt[p] ? !1 : !us[i] && (Yr[i] || !cs[i]);
  }, ei = function(i) {
    const l = Dt(i), p = $e(je(i)), h = V(i);
    let _, x;
    return h && M(h) === L.element ? (_ = { namespaceURI: Dt(h) }, x = $e(je(h))) : (_ = { namespaceURI: De }, x = "template"), Yt[l] ? l === bt ? Kr(p, _, x) : l === mt ? Qr(p, _, x) : l === re ? Jr(p, _, x) : !!(Ye === "application/xhtml+xml" && Yt[l]) : !1;
  }, de = function(i) {
    Qe(e.removed, { element: i });
    try {
      V(i).removeChild(i);
    } catch {
      if (y(i), !V(i)) throw ce("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place");
    }
  }, ps = function(i, l, p) {
    try {
      k(i, l);
    } catch {
      try {
        i.removeAttribute(p);
      } catch {
      }
    }
  }, Kt = function(i) {
    Jt(i);
    const l = X(i);
    l && le(Qi(l), (h) => {
      try {
        y(h);
      } catch {
      }
    });
    const p = M(i) === L.element ? Oe(i) : null;
    if (p) for (let h = p.length - 1; h >= 0; --h) {
      const _ = p[h], x = _ && _.name;
      typeof x == "string" && ps(i, _, x);
    }
  }, Ne = function(i, l, p) {
    if (!p) try {
      p = l.getAttributeNode(i);
    } catch {
      p = null;
    }
    Qe(e.removed, {
      attribute: p || null,
      from: l
    });
    try {
      p ? k(l, p) : l.removeAttribute(i);
    } catch {
      try {
        l.removeAttribute(i);
      } catch {
      }
    }
    if (i === "is")
      if (Pe || ft) try {
        de(l);
      } catch {
      }
      else try {
        l.setAttribute(i, "");
      } catch {
      }
  }, hs = function(i) {
    const l = Oe(i);
    if (l)
      for (let p = l.length - 1; p >= 0; --p) {
        const h = l[p], _ = h && h.name;
        typeof _ != "string" || O[P(_)] || ps(i, h, _);
      }
  }, Qt = function(i, l) {
    let p = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : !1;
    const h = [i];
    for (; h.length > 0; ) {
      const _ = h.pop();
      if (l(_) === !1) continue;
      if (p && M(_) === L.element) {
        const w = Ie(_);
        fe(w) && h.push(w);
      }
      const x = X(_);
      if (x) for (let w = x.length - 1; w >= 0; --w) h.push(x[w]);
    }
  }, Jt = function(i) {
    Qt(i, (l) => {
      M(l) === L.element && hs(l);
    });
  }, en = function(i) {
    const l = [];
    return Qt(i, (p) => {
      l.push(p);
    }, !0), l;
  }, ti = function(i, l) {
    const p = cn();
    le(en(i), (h) => {
      M(h) === L.element && un(p, h);
    }), le(l, (h) => {
      M(h) === L.element && !Je(p, h) && hs(h);
    });
  }, ds = function(i, l) {
    let p = !1;
    return le(e.removed, (h) => {
      h.element && (p = p || h.element === i, Jt(h.element));
    }), ti(i, l), p;
  }, ni = 8, si = function(i, l) {
    const p = ke;
    let h = null;
    const _ = () => (h || (h = cn(), le(l, (x) => {
      un(h, x);
    })), h);
    for (let x = 0; ; x++) {
      const w = en(i), D = [i];
      let ie = !1;
      if (le(w, (B) => {
        M(B) === L.documentFragment ? Qe(D, B) : !ie && !Je(p, B) && (ie = Je(_(), B));
      }), !ie) return;
      if (x >= ni) throw ce("the tree kept changing during in-place sanitization; refusing to return it");
      le(D, (B, G) => {
        ri(B, G > 0, i, _());
      });
    }
  }, ri = function(i, l, p, h) {
    const _ = tn(i);
    let x;
    for (; x = _.nextNode(); )
      !Je(h, x) || Je(ke, x) || (l && Q(E.uponSanitizeShadowNode, x, null), sn(x, p), rn(x, p), fe(x.content) && Ze(x.content));
  }, ii = function(i) {
    ke && un(ke, i);
  }, fs = function(i, l) {
    return ye ? i === "patchsrc" ? !0 : i === "for" && l !== "label" && l !== "output" : !1;
  }, oi = function(i) {
    ye && Qt(i, (l) => {
      const p = M(l);
      if (p === L.processingInstruction || p === L.comment && z(Vs, l.data)) {
        try {
          y(l);
        } catch {
        }
        return !1;
      }
      if (p === L.element) {
        const h = l, _ = P(je(l));
        try {
          h.hasAttribute && h.hasAttribute("patchsrc") && h.removeAttribute("patchsrc"), h.hasAttribute && h.hasAttribute("for") && fs("for", _) && h.removeAttribute("for");
        } catch {
        }
      }
      return !0;
    });
  }, gs = function(i) {
    let l = null, p = null;
    if (Wt) i = "<remove></remove>" + i;
    else {
      const x = Us(i, /^[\r\n\t ]+/);
      p = x && x[0];
    }
    Ye === "application/xhtml+xml" && De === re && (i = '<html xmlns="http://www.w3.org/1999/xhtml"><head></head><body>' + i + "</body></html>");
    const h = j ? Ce(i) : i;
    if (De === re) try {
      l = new m().parseFromString(h, Ye);
    } catch {
    }
    if (!l || !l.documentElement) {
      l = Nt.createDocument(De, "template", null);
      try {
        l.documentElement.innerHTML = qt ? _e : h;
      } catch {
      }
    }
    const _ = l.body || l.documentElement;
    return i && p && _.insertBefore(t.createTextNode(p), _.childNodes[0] || null), De === re ? Nr.call(l, xe ? "html" : "body")[0] : xe ? l.documentElement : _;
  }, tn = function(i) {
    const l = pe ? pe(i) : i.ownerDocument;
    return qn.call(l || i, i, c.SHOW_ELEMENT | c.SHOW_COMMENT | c.SHOW_TEXT | c.SHOW_PROCESSING_INSTRUCTION | c.SHOW_CDATA_SECTION, null);
  }, _t = function(i) {
    return i = et(i, Ur, " "), i = et(i, Hr, " "), i = et(i, Br, " "), i;
  }, nn = function(i) {
    var l;
    ms(i);
    const p = (l = i.querySelectorAll) === null || l === void 0 ? void 0 : l.call(i, "template");
    p && le(p, (h) => {
      fe(h.content) && nn(h.content);
    });
  }, ms = function(i) {
    i.normalize();
    const l = pe ? pe(i) : i.ownerDocument, p = qn.call(l || i, i, c.SHOW_TEXT | c.SHOW_COMMENT | c.SHOW_CDATA_SECTION | c.SHOW_PROCESSING_INSTRUCTION, null);
    let h = p.nextNode();
    for (; h; )
      h.data = _t(h.data), h = p.nextNode();
  }, yt = function(i) {
    const l = ue ? ue(i) : null;
    return typeof l != "string" || P(l) !== "form" ? !1 : typeof i.nodeName != "string" || typeof i.textContent != "string" || typeof i.removeChild != "function" || i.attributes !== Oe(i) || typeof i.removeAttribute != "function" || typeof i.removeAttributeNode != "function" || typeof i.getAttributeNode != "function" || typeof i.setAttribute != "function" || typeof i.namespaceURI != "string" || typeof i.insertBefore != "function" || typeof i.hasChildNodes != "function" || i.nodeType !== ne(i) || i.childNodes !== X(i);
  }, fe = function(i) {
    if (!ne || typeof i != "object" || i === null) return !1;
    try {
      return ne(i) === L.documentFragment;
    } catch {
      return !1;
    }
  }, Ve = function(i) {
    if (!ne || typeof i != "object" || i === null) return !1;
    try {
      return typeof ne(i) == "number";
    } catch {
      return !1;
    }
  };
  function Q(d, i, l) {
    d.length !== 0 && le(d, (p) => {
      p.call(e, i, l, Me);
    });
  }
  const ai = function(i, l) {
    return !!(ye && i.hasChildNodes() && !Ve(i.firstElementChild) && z(mn, i.textContent) && z(mn, i.innerHTML) || ye && xo[l] && M(i) === L.element && Dt(i) === re && (Ve(i.firstElementChild) || typeof i.textContent == "string" && z(mn, i.textContent)) || i.nodeType === L.processingInstruction || ye && i.nodeType === L.comment && z(Vs, i.data));
  }, xt = function(i, l) {
    if (i instanceof RegExp) return z(i, l);
    if (i instanceof Function) {
      for (var p = arguments.length, h = new Array(p > 2 ? p - 2 : 0), _ = 2; _ < p; _++) h[_ - 2] = arguments[_];
      return !!i(l, ...h);
    }
    return !1;
  }, li = function(i, l, p) {
    if (!qe[l] && ys(l) && xt(se.tagNameCheck, l)) return !1;
    if (jt && !we[l] && !we[$e(l)]) {
      const h = V(i), _ = X(i);
      if (_ && h) {
        const x = _.length;
        for (let w = x - 1; w >= 0; --w) {
          const D = i === p ? b(_[w], !0) : _[w];
          h.insertBefore(D, R(i));
        }
      }
    }
    return de(i), !0;
  }, bs = function(i, l, p, h) {
    return i.length === 0 ? l : l === p || l === h ? Z(l) : l;
  }, ze = function(i, l) {
    return i === l || V(i) !== null ? !1 : (Gt && Jt(i), !0);
  }, sn = function(i, l) {
    if (ii(i), Q(E.beforeSanitizeElements, i, null), ze(i, l)) return !0;
    if (yt(i))
      return de(i), !0;
    const p = P(je(i));
    if (I = bs(E.uponSanitizeElement, I, zt, ht), Q(E.uponSanitizeElement, i, {
      tagName: p,
      allowedTags: I
    }), ze(i, l)) return !0;
    if (ai(i, p))
      return de(i), !0;
    if (qe[p] || !(he.tagCheck instanceof Function && he.tagCheck(p)) && !I[p]) {
      const h = li(i, p, l);
      return h === !1 && (Q(E.afterSanitizeElements, i, null), ze(i, l)) ? !0 : h;
    }
    if (M(i) === L.element && !ei(i) || (p === "noscript" || p === "noembed" || p === "noframes") && z(yo, i.innerHTML))
      return de(i), !0;
    if (ae && i.nodeType === L.text) {
      const h = _t(i.textContent);
      i.textContent !== h && (Qe(e.removed, { element: i.cloneNode() }), i.textContent = h);
    }
    return Q(E.afterSanitizeElements, i, null), ze(i, l);
  }, _s = function(i, l, p) {
    if (Zn[l] || fs(l, i) || Qn && (l === "id" || l === "name") && (p in t || p in Xr)) return !1;
    const h = O[l] || he.attributeCheck instanceof Function && he.attributeCheck(l, i);
    return Ht && z(Fr, l) || Xn && z(Wr, l) ? !0 : h ? rs[l] || z(Vn, et(p, Yn, "")) || (l === "src" || l === "xlink:href" || l === "href") && i !== "script" && Hs(p, "data:") === 0 && ns[i] || Kn && !z(jr, et(p, Yn, "")) ? !0 : !p : ys(i) && xt(se.tagNameCheck, i) && xt(se.attributeNameCheck, l, i) || l === "is" && se.allowCustomizedBuiltInElements && xt(se.tagNameCheck, p);
  }, ci = A({}, [
    "annotation-xml",
    "color-profile",
    "font-face",
    "font-face-format",
    "font-face-name",
    "font-face-src",
    "font-face-uri",
    "missing-glyph"
  ]), ys = function(i) {
    return !ci[$e(i)] && z(Gr, i);
  }, ui = function(i, l, p, h) {
    if (j && typeof g == "object" && typeof g.getAttributeType == "function" && !p) switch (g.getAttributeType(i, l)) {
      case "TrustedHTML":
        return Ce(h);
      case "TrustedScriptURL":
        return Lr(h);
    }
    return h;
  }, pi = function(i, l, p, h) {
    try {
      return p ? i.setAttributeNS(p, l, h) : i.setAttribute(l, h), yt(i) ? (de(i), !1) : !0;
    } catch {
      return Ne(l, i), !1;
    }
  }, xs = function(i, l) {
    return ye && z(/((--!?|])>)|<\/(style|script|title|xmp|textarea|noscript|iframe|noembed|noframes)/i, l) ? !0 : $e(i) === "attributename" && Us(l, "href") !== null;
  }, rn = function(i, l) {
    if (Q(E.beforeSanitizeAttributes, i, null), ze(i, l)) return;
    const p = i.attributes;
    if (!p || yt(i)) return;
    O = bs(E.uponSanitizeAttribute, O, Ut, dt);
    const h = {
      attrName: "",
      attrValue: "",
      keepAttr: !0,
      allowedAttributes: O,
      forceKeepAttr: void 0
    };
    let _ = p.length;
    const x = P(i.nodeName);
    for (; _--; ) {
      const w = p[_], D = w.name, ie = w.namespaceURI, B = w.value, G = P(D), Ue = B;
      let q = D === "value" ? Ue : eo(Ue), ks = !1;
      if (h.attrName = G, h.attrValue = q, h.keepAttr = !0, h.forceKeepAttr = void 0, Q(E.uponSanitizeAttribute, i, h), q = h.attrValue, Jn && (G === "id" || G === "name") && Hs(q, es) !== 0 && (Ne(D, i, w), q = es + q, ks = !0), xs(D, q)) {
        Ne(D, i, w);
        continue;
      }
      if (!h.forceKeepAttr) {
        if (!h.keepAttr) {
          Ne(D, i, w);
          continue;
        }
        if (!Bt && z(Zs, q)) {
          Ne(D, i, w);
          continue;
        }
        if (ae && (q = _t(q)), !_s(x, G, q)) {
          Ne(D, i, w);
          continue;
        }
        q = ui(x, G, ie, q), q !== Ue && pi(i, D, ie, q) && ks && zs(e.removed);
      }
    }
    Q(E.afterSanitizeAttributes, i, null), ze(i, l);
  }, Ze = function(i) {
    let l = null;
    const p = tn(i);
    for (Q(E.beforeSanitizeShadowDOM, i, null); l = p.nextNode(); )
      if (Q(E.uponSanitizeShadowNode, l, null), sn(l, i), rn(l, i), fe(l.content) && Ze(l.content), M(l) === L.element) {
        const h = Ie(l);
        fe(h) && (on(h), Ze(h));
      }
    ae && ms(i), Q(E.afterSanitizeShadowDOM, i, null);
  }, on = function(i) {
    const l = [{
      node: i,
      shadow: null
    }];
    for (; l.length > 0; ) {
      const p = l.pop();
      if (p.shadow) {
        Ze(p.shadow);
        continue;
      }
      const h = p.node, _ = M(h) === L.element, x = X(h);
      if (x) for (let w = x.length - 1; w >= 0; --w) l.push({
        node: x[w],
        shadow: null
      });
      if (_) {
        const w = ue ? ue(h) : null;
        if (typeof w == "string" && P(w) === "template") {
          const D = h.content;
          fe(D) && l.push({
            node: D,
            shadow: null
          });
        }
      }
      if (_) {
        const w = Ie(h);
        fe(w) && l.push({
          node: null,
          shadow: w
        }, {
          node: w,
          shadow: null
        });
      }
    }
  };
  return e.sanitize = function(d) {
    let i = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {}, l = null, p = null, h = null, _ = null;
    if (qt = !d, qt && (d = "<!-->"), typeof d != "string" && !Ve(d) && (d = ro(d), typeof d != "string"))
      throw ce("dirty is not a string, aborting");
    if (!e.isSupported) return d;
    Ft ? (I = ht, O = dt) : Xt(i), (E.uponSanitizeElement.length > 0 || E.uponSanitizeAttribute.length > 0) && (I = Z(I)), E.uponSanitizeAttribute.length > 0 && (O = Z(O)), e.removed = [];
    const x = Gt && typeof d != "string" && Ve(d);
    let w = [];
    const D = ke;
    if (x) {
      oi(d);
      const G = je(d);
      if (typeof G == "string") {
        const Ue = P(G);
        if (!I[Ue] || qe[Ue])
          throw Kt(d), ce("root node is forbidden and cannot be sanitized in-place");
      }
      if (yt(d))
        throw Kt(d), ce("root node is clobbered and cannot be sanitized in-place");
      w = en(d), ke = cn();
    } else if (Ve(d))
      l = gs("<!---->"), p = l.ownerDocument.importNode(d, !0), p.nodeType === L.element && p.nodeName === "BODY" || p.nodeName === "HTML" ? l = p : l.appendChild(p), on(l);
    else {
      if (!Pe && !ae && !xe && d.indexOf("<") === -1) return j && gt ? Ce(d) : d;
      if (l = gs(d), !l) return Pe ? null : gt ? _e : "";
    }
    l && Wt && de(l.firstChild);
    const ie = x ? d : l;
    try {
      x && on(d);
      const G = tn(ie);
      for (; h = G.nextNode(); )
        sn(h, ie), rn(h, ie), fe(h.content) && Ze(h.content);
      x && si(d, w);
    } catch (G) {
      throw x && (Kt(d), ds(d, w)), G;
    } finally {
      ke = D;
    }
    if (x) {
      if (ds(d, w)) throw ce("a node selected for removal could not be safely returned; refusing to sanitize in place");
      return ae && nn(d), d;
    }
    if (Pe) {
      if (ae && nn(l), ft)
        for (_ = Mr.call(l.ownerDocument); l.firstChild; ) _.appendChild(l.firstChild);
      else _ = l;
      return (O.shadowroot || O.shadowrootmode) && (_ = zr.call(r, _, !0)), _;
    }
    let B = xe ? l.outerHTML : l.innerHTML;
    return xe && I["!doctype"] && l.ownerDocument && l.ownerDocument.doctype && l.ownerDocument.doctype.name && z(bo, l.ownerDocument.doctype.name) && (B = "<!DOCTYPE " + l.ownerDocument.doctype.name + `>
` + B), ae && (B = _t(B)), j && gt ? Ce(B) : B;
  }, e.setConfig = function() {
    let d = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
    Xt(d), Ft = !0, ht = I, dt = O;
  }, e.clearConfig = function() {
    Me = null, Ft = !1, ht = null, dt = null, j = Mt, _e = "";
  }, e.isValidAttribute = function(d, i, l) {
    Me || Xt({});
    const p = P(d), h = P(i);
    return typeof l == "string" && (xs(i, l) || !Bt && z(Zs, l)) ? !1 : _s(p, h, l);
  }, e.addHook = function(d, i) {
    typeof i == "function" && Y(E, d) && Qe(E[d], i);
  }, e.removeHook = function(d, i) {
    if (Y(E, d)) {
      if (i !== void 0) {
        const l = Ki(E[d], i);
        return l === -1 ? void 0 : Ji(E[d], l, 1)[0];
      }
      return zs(E[d]);
    }
  }, e.removeHooks = function(d) {
    Y(E, d) && (E[d] = []);
  }, e.removeAllHooks = function() {
    E = Xs();
  }, e;
}
var kr = xr();
function Ln() {
  return { async: !1, breaks: !1, extensions: null, gfm: !0, hooks: null, pedantic: !1, renderer: null, silent: !1, tokenizer: null, walkTokens: null };
}
var Re = Ln();
function wr(n) {
  Re = n;
}
var at = { exec: () => null };
function v(n, e = "") {
  let t = typeof n == "string" ? n : n.source, r = { replace: (s, a) => {
    let o = typeof a == "string" ? a : a.source;
    return o = o.replace(F.caret, "$1"), t = t.replace(s, o), r;
  }, getRegex: () => new RegExp(t, e) };
  return r;
}
var Ao = (() => {
  try {
    return !!new RegExp("(?<=1)(?<!1)");
  } catch {
    return !1;
  }
})(), F = { codeRemoveIndent: /^(?: {1,4}| {0,3}\t)/gm, outputLinkReplace: /\\([\[\]])/g, indentCodeCompensation: /^(\s+)(?:```)/, beginningSpace: /^\s+/, endingHash: /#$/, startingSpaceChar: /^ /, endingSpaceChar: / $/, nonSpaceChar: /[^ ]/, newLineCharGlobal: /\n/g, tabCharGlobal: /\t/g, multipleSpaceGlobal: /\s+/g, blankLine: /^[ \t]*$/, doubleBlankLine: /\n[ \t]*\n[ \t]*$/, blockquoteStart: /^ {0,3}>/, blockquoteSetextReplace: /\n {0,3}((?:=+|-+) *)(?=\n|$)/g, blockquoteSetextReplace2: /^ {0,3}>[ \t]?/gm, listReplaceTabs: /^\t+/, listReplaceNesting: /^ {1,4}(?=( {4})*[^ ])/g, listIsTask: /^\[[ xX]\] /, listReplaceTask: /^\[[ xX]\] +/, anyLine: /\n.*\n/, hrefBrackets: /^<(.*)>$/, tableDelimiter: /[:|]/, tableAlignChars: /^\||\| *$/g, tableRowBlankLine: /\n[ \t]*$/, tableAlignRight: /^ *-+: *$/, tableAlignCenter: /^ *:-+: *$/, tableAlignLeft: /^ *:-+ *$/, startATag: /^<a /i, endATag: /^<\/a>/i, startPreScriptTag: /^<(pre|code|kbd|script)(\s|>)/i, endPreScriptTag: /^<\/(pre|code|kbd|script)(\s|>)/i, startAngleBracket: /^</, endAngleBracket: />$/, pedanticHrefTitle: /^([^'"]*[^\s])\s+(['"])(.*)\2/, unicodeAlphaNumeric: /[\p{L}\p{N}]/u, escapeTest: /[&<>"']/, escapeReplace: /[&<>"']/g, escapeTestNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/, escapeReplaceNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g, unescapeTest: /&(#(?:\d+)|(?:#x[0-9A-Fa-f]+)|(?:\w+));?/ig, caret: /(^|[^\[])\^/g, percentDecode: /%25/g, findPipe: /\|/g, splitPipe: / \|/, slashPipe: /\\\|/g, carriageReturn: /\r\n|\r/g, spaceLine: /^ +$/gm, notSpaceStart: /^\S*/, endingNewline: /\n$/, listItemRegex: (n) => new RegExp(`^( {0,3}${n})((?:[	 ][^\\n]*)?(?:\\n|$))`), nextBulletRegex: (n) => new RegExp(`^ {0,${Math.min(3, n - 1)}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`), hrRegex: (n) => new RegExp(`^ {0,${Math.min(3, n - 1)}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`), fencesBeginRegex: (n) => new RegExp(`^ {0,${Math.min(3, n - 1)}}(?:\`\`\`|~~~)`), headingBeginRegex: (n) => new RegExp(`^ {0,${Math.min(3, n - 1)}}#`), htmlBeginRegex: (n) => new RegExp(`^ {0,${Math.min(3, n - 1)}}<(?:[a-z].*>|!--)`, "i") }, vo = /^(?:[ \t]*(?:\n|$))+/, $o = /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, To = /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, ut = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, So = /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, Dn = /(?:[*+-]|\d{1,9}[.)])/, Ar = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, vr = v(Ar).replace(/bull/g, Dn).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), Eo = v(Ar).replace(/bull/g, Dn).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), Mn = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table| +\n)[^\n]+)*)/, Ro = /^[^\n]+/, Nn = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, Io = v(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", Nn).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), Oo = v(/^( {0,3}bull)([ \t][^\n]+?)?(?:\n|$)/).replace(/bull/g, Dn).getRegex(), Pt = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", zn = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, Co = v("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n+|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>\\n*|$)|<![A-Z][\\s\\S]*?(?:>\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", zn).replace("tag", Pt).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), $r = v(Mn).replace("hr", ut).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Pt).getRegex(), Po = v(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", $r).getRegex(), Un = { blockquote: Po, code: $o, def: Io, fences: To, heading: So, hr: ut, html: Co, lheading: vr, list: Oo, newline: vo, paragraph: $r, table: at, text: Ro }, Ks = v("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", ut).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Pt).getRegex(), Lo = { ...Un, lheading: Eo, table: Ks, paragraph: v(Mn).replace("hr", ut).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", Ks).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)]) ").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Pt).getRegex() }, Do = { ...Un, html: v(`^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:"[^"]*"|'[^']*'|\\s[^'"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))`).replace("comment", zn).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(), def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/, heading: /^(#{1,6})(.*)(?:\n+|$)/, fences: at, lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/, paragraph: v(Mn).replace("hr", ut).replace("heading", ` *#{1,6} *[^
]`).replace("lheading", vr).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex() }, Mo = /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, No = /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, Tr = /^( {2,}|\\)\n(?!\s*$)/, zo = /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, Lt = /[\p{P}\p{S}]/u, Hn = /[\s\p{P}\p{S}]/u, Sr = /[^\s\p{P}\p{S}]/u, Uo = v(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, Hn).getRegex(), Er = /(?!~)[\p{P}\p{S}]/u, Ho = /(?!~)[\s\p{P}\p{S}]/u, Bo = /(?:[^\s\p{P}\p{S}]|~)/u, Fo = v(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", Ao ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), Rr = /^(?:\*+(?:((?!\*)punct)|[^\s*]))|^_+(?:((?!_)punct)|([^\s_]))/, Wo = v(Rr, "u").replace(/punct/g, Lt).getRegex(), jo = v(Rr, "u").replace(/punct/g, Er).getRegex(), Ir = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", Go = v(Ir, "gu").replace(/notPunctSpace/g, Sr).replace(/punctSpace/g, Hn).replace(/punct/g, Lt).getRegex(), qo = v(Ir, "gu").replace(/notPunctSpace/g, Bo).replace(/punctSpace/g, Ho).replace(/punct/g, Er).getRegex(), Yo = v("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, Sr).replace(/punctSpace/g, Hn).replace(/punct/g, Lt).getRegex(), Vo = v(/\\(punct)/, "gu").replace(/punct/g, Lt).getRegex(), Zo = v(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), Xo = v(zn).replace("(?:-->|$)", "-->").getRegex(), Ko = v("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", Xo).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), St = /(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+[^`]*?`+(?!`)|[^\[\]\\`])*?/, Qo = v(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]*(?:\n[ \t]*)?)(title))?\s*\)/).replace("label", St).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]*/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), Or = v(/^!?\[(label)\]\[(ref)\]/).replace("label", St).replace("ref", Nn).getRegex(), Cr = v(/^!?\[(ref)\](?:\[\])?/).replace("ref", Nn).getRegex(), Jo = v("reflink|nolink(?!\\()", "g").replace("reflink", Or).replace("nolink", Cr).getRegex(), Qs = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, Bn = { _backpedal: at, anyPunctuation: Vo, autolink: Zo, blockSkip: Fo, br: Tr, code: No, del: at, emStrongLDelim: Wo, emStrongRDelimAst: Go, emStrongRDelimUnd: Yo, escape: Mo, link: Qo, nolink: Cr, punctuation: Uo, reflink: Or, reflinkSearch: Jo, tag: Ko, text: zo, url: at }, ea = { ...Bn, link: v(/^!?\[(label)\]\((.*?)\)/).replace("label", St).getRegex(), reflink: v(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", St).getRegex() }, vn = { ...Bn, emStrongRDelimAst: qo, emStrongLDelim: jo, url: v(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol", Qs).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(), _backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/, del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/, text: v(/^([`~]+|[^`~])(?:(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol", Qs).getRegex() }, ta = { ...vn, br: v(Tr).replace("{2,}", "*").getRegex(), text: v(vn.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex() }, wt = { normal: Un, gfm: Lo, pedantic: Do }, nt = { normal: Bn, gfm: vn, breaks: ta, pedantic: ea }, na = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }, Js = (n) => na[n];
function oe(n, e) {
  if (e) {
    if (F.escapeTest.test(n)) return n.replace(F.escapeReplace, Js);
  } else if (F.escapeTestNoEncode.test(n)) return n.replace(F.escapeReplaceNoEncode, Js);
  return n;
}
function er(n) {
  try {
    n = encodeURI(n).replace(F.percentDecode, "%");
  } catch {
    return null;
  }
  return n;
}
function tr(n, e) {
  let t = n.replace(F.findPipe, (a, o, u) => {
    let c = !1, m = o;
    for (; --m >= 0 && u[m] === "\\"; ) c = !c;
    return c ? "|" : " |";
  }), r = t.split(F.splitPipe), s = 0;
  if (r[0].trim() || r.shift(), r.length > 0 && !r.at(-1)?.trim() && r.pop(), e) if (r.length > e) r.splice(e);
  else for (; r.length < e; ) r.push("");
  for (; s < r.length; s++) r[s] = r[s].trim().replace(F.slashPipe, "|");
  return r;
}
function st(n, e, t) {
  let r = n.length;
  if (r === 0) return "";
  let s = 0;
  for (; s < r && n.charAt(r - s - 1) === e; )
    s++;
  return n.slice(0, r - s);
}
function sa(n, e) {
  if (n.indexOf(e[1]) === -1) return -1;
  let t = 0;
  for (let r = 0; r < n.length; r++) if (n[r] === "\\") r++;
  else if (n[r] === e[0]) t++;
  else if (n[r] === e[1] && (t--, t < 0)) return r;
  return t > 0 ? -2 : -1;
}
function nr(n, e, t, r, s) {
  let a = e.href, o = e.title || null, u = n[1].replace(s.other.outputLinkReplace, "$1");
  r.state.inLink = !0;
  let c = { type: n[0].charAt(0) === "!" ? "image" : "link", raw: t, href: a, title: o, text: u, tokens: r.inlineTokens(u) };
  return r.state.inLink = !1, c;
}
function ra(n, e, t) {
  let r = n.match(t.other.indentCodeCompensation);
  if (r === null) return e;
  let s = r[1];
  return e.split(`
`).map((a) => {
    let o = a.match(t.other.beginningSpace);
    if (o === null) return a;
    let [u] = o;
    return u.length >= s.length ? a.slice(s.length) : a;
  }).join(`
`);
}
var Et = class {
  options;
  rules;
  lexer;
  constructor(n) {
    this.options = n || Re;
  }
  space(n) {
    let e = this.rules.block.newline.exec(n);
    if (e && e[0].length > 0) return { type: "space", raw: e[0] };
  }
  code(n) {
    let e = this.rules.block.code.exec(n);
    if (e) {
      let t = e[0].replace(this.rules.other.codeRemoveIndent, "");
      return { type: "code", raw: e[0], codeBlockStyle: "indented", text: this.options.pedantic ? t : st(t, `
`) };
    }
  }
  fences(n) {
    let e = this.rules.block.fences.exec(n);
    if (e) {
      let t = e[0], r = ra(t, e[3] || "", this.rules);
      return { type: "code", raw: t, lang: e[2] ? e[2].trim().replace(this.rules.inline.anyPunctuation, "$1") : e[2], text: r };
    }
  }
  heading(n) {
    let e = this.rules.block.heading.exec(n);
    if (e) {
      let t = e[2].trim();
      if (this.rules.other.endingHash.test(t)) {
        let r = st(t, "#");
        (this.options.pedantic || !r || this.rules.other.endingSpaceChar.test(r)) && (t = r.trim());
      }
      return { type: "heading", raw: e[0], depth: e[1].length, text: t, tokens: this.lexer.inline(t) };
    }
  }
  hr(n) {
    let e = this.rules.block.hr.exec(n);
    if (e) return { type: "hr", raw: st(e[0], `
`) };
  }
  blockquote(n) {
    let e = this.rules.block.blockquote.exec(n);
    if (e) {
      let t = st(e[0], `
`).split(`
`), r = "", s = "", a = [];
      for (; t.length > 0; ) {
        let o = !1, u = [], c;
        for (c = 0; c < t.length; c++) if (this.rules.other.blockquoteStart.test(t[c])) u.push(t[c]), o = !0;
        else if (!o) u.push(t[c]);
        else break;
        t = t.slice(c);
        let m = u.join(`
`), g = m.replace(this.rules.other.blockquoteSetextReplace, `
    $1`).replace(this.rules.other.blockquoteSetextReplace2, "");
        r = r ? `${r}
${m}` : m, s = s ? `${s}
${g}` : g;
        let f = this.lexer.state.top;
        if (this.lexer.state.top = !0, this.lexer.blockTokens(g, a, !0), this.lexer.state.top = f, t.length === 0) break;
        let b = a.at(-1);
        if (b?.type === "code") break;
        if (b?.type === "blockquote") {
          let y = b, k = y.raw + `
` + t.join(`
`), R = this.blockquote(k);
          a[a.length - 1] = R, r = r.substring(0, r.length - y.raw.length) + R.raw, s = s.substring(0, s.length - y.text.length) + R.text;
          break;
        } else if (b?.type === "list") {
          let y = b, k = y.raw + `
` + t.join(`
`), R = this.list(k);
          a[a.length - 1] = R, r = r.substring(0, r.length - b.raw.length) + R.raw, s = s.substring(0, s.length - y.raw.length) + R.raw, t = k.substring(a.at(-1).raw.length).split(`
`);
          continue;
        }
      }
      return { type: "blockquote", raw: r, tokens: a, text: s };
    }
  }
  list(n) {
    let e = this.rules.block.list.exec(n);
    if (e) {
      let t = e[1].trim(), r = t.length > 1, s = { type: "list", raw: "", ordered: r, start: r ? +t.slice(0, -1) : "", loose: !1, items: [] };
      t = r ? `\\d{1,9}\\${t.slice(-1)}` : `\\${t}`, this.options.pedantic && (t = r ? t : "[*+-]");
      let a = this.rules.other.listItemRegex(t), o = !1;
      for (; n; ) {
        let c = !1, m = "", g = "";
        if (!(e = a.exec(n)) || this.rules.block.hr.test(n)) break;
        m = e[0], n = n.substring(m.length);
        let f = e[2].split(`
`, 1)[0].replace(this.rules.other.listReplaceTabs, (V) => " ".repeat(3 * V.length)), b = n.split(`
`, 1)[0], y = !f.trim(), k = 0;
        if (this.options.pedantic ? (k = 2, g = f.trimStart()) : y ? k = e[1].length + 1 : (k = e[2].search(this.rules.other.nonSpaceChar), k = k > 4 ? 1 : k, g = f.slice(k), k += e[1].length), y && this.rules.other.blankLine.test(b) && (m += b + `
`, n = n.substring(b.length + 1), c = !0), !c) {
          let V = this.rules.other.nextBulletRegex(k), Ie = this.rules.other.hrRegex(k), Oe = this.rules.other.fencesBeginRegex(k), ne = this.rules.other.headingBeginRegex(k), ue = this.rules.other.htmlBeginRegex(k);
          for (; n; ) {
            let pe = n.split(`
`, 1)[0], M;
            if (b = pe, this.options.pedantic ? (b = b.replace(this.rules.other.listReplaceNesting, "  "), M = b) : M = b.replace(this.rules.other.tabCharGlobal, "    "), Oe.test(b) || ne.test(b) || ue.test(b) || V.test(b) || Ie.test(b)) break;
            if (M.search(this.rules.other.nonSpaceChar) >= k || !b.trim()) g += `
` + M.slice(k);
            else {
              if (y || f.replace(this.rules.other.tabCharGlobal, "    ").search(this.rules.other.nonSpaceChar) >= 4 || Oe.test(f) || ne.test(f) || Ie.test(f)) break;
              g += `
` + b;
            }
            !y && !b.trim() && (y = !0), m += pe + `
`, n = n.substring(pe.length + 1), f = M.slice(k);
          }
        }
        s.loose || (o ? s.loose = !0 : this.rules.other.doubleBlankLine.test(m) && (o = !0));
        let R = null, X;
        this.options.gfm && (R = this.rules.other.listIsTask.exec(g), R && (X = R[0] !== "[ ] ", g = g.replace(this.rules.other.listReplaceTask, ""))), s.items.push({ type: "list_item", raw: m, task: !!R, checked: X, loose: !1, text: g, tokens: [] }), s.raw += m;
      }
      let u = s.items.at(-1);
      if (u) u.raw = u.raw.trimEnd(), u.text = u.text.trimEnd();
      else return;
      s.raw = s.raw.trimEnd();
      for (let c = 0; c < s.items.length; c++) if (this.lexer.state.top = !1, s.items[c].tokens = this.lexer.blockTokens(s.items[c].text, []), !s.loose) {
        let m = s.items[c].tokens.filter((f) => f.type === "space"), g = m.length > 0 && m.some((f) => this.rules.other.anyLine.test(f.raw));
        s.loose = g;
      }
      if (s.loose) for (let c = 0; c < s.items.length; c++) s.items[c].loose = !0;
      return s;
    }
  }
  html(n) {
    let e = this.rules.block.html.exec(n);
    if (e) return { type: "html", block: !0, raw: e[0], pre: e[1] === "pre" || e[1] === "script" || e[1] === "style", text: e[0] };
  }
  def(n) {
    let e = this.rules.block.def.exec(n);
    if (e) {
      let t = e[1].toLowerCase().replace(this.rules.other.multipleSpaceGlobal, " "), r = e[2] ? e[2].replace(this.rules.other.hrefBrackets, "$1").replace(this.rules.inline.anyPunctuation, "$1") : "", s = e[3] ? e[3].substring(1, e[3].length - 1).replace(this.rules.inline.anyPunctuation, "$1") : e[3];
      return { type: "def", tag: t, raw: e[0], href: r, title: s };
    }
  }
  table(n) {
    let e = this.rules.block.table.exec(n);
    if (!e || !this.rules.other.tableDelimiter.test(e[2])) return;
    let t = tr(e[1]), r = e[2].replace(this.rules.other.tableAlignChars, "").split("|"), s = e[3]?.trim() ? e[3].replace(this.rules.other.tableRowBlankLine, "").split(`
`) : [], a = { type: "table", raw: e[0], header: [], align: [], rows: [] };
    if (t.length === r.length) {
      for (let o of r) this.rules.other.tableAlignRight.test(o) ? a.align.push("right") : this.rules.other.tableAlignCenter.test(o) ? a.align.push("center") : this.rules.other.tableAlignLeft.test(o) ? a.align.push("left") : a.align.push(null);
      for (let o = 0; o < t.length; o++) a.header.push({ text: t[o], tokens: this.lexer.inline(t[o]), header: !0, align: a.align[o] });
      for (let o of s) a.rows.push(tr(o, a.header.length).map((u, c) => ({ text: u, tokens: this.lexer.inline(u), header: !1, align: a.align[c] })));
      return a;
    }
  }
  lheading(n) {
    let e = this.rules.block.lheading.exec(n);
    if (e) return { type: "heading", raw: e[0], depth: e[2].charAt(0) === "=" ? 1 : 2, text: e[1], tokens: this.lexer.inline(e[1]) };
  }
  paragraph(n) {
    let e = this.rules.block.paragraph.exec(n);
    if (e) {
      let t = e[1].charAt(e[1].length - 1) === `
` ? e[1].slice(0, -1) : e[1];
      return { type: "paragraph", raw: e[0], text: t, tokens: this.lexer.inline(t) };
    }
  }
  text(n) {
    let e = this.rules.block.text.exec(n);
    if (e) return { type: "text", raw: e[0], text: e[0], tokens: this.lexer.inline(e[0]) };
  }
  escape(n) {
    let e = this.rules.inline.escape.exec(n);
    if (e) return { type: "escape", raw: e[0], text: e[1] };
  }
  tag(n) {
    let e = this.rules.inline.tag.exec(n);
    if (e) return !this.lexer.state.inLink && this.rules.other.startATag.test(e[0]) ? this.lexer.state.inLink = !0 : this.lexer.state.inLink && this.rules.other.endATag.test(e[0]) && (this.lexer.state.inLink = !1), !this.lexer.state.inRawBlock && this.rules.other.startPreScriptTag.test(e[0]) ? this.lexer.state.inRawBlock = !0 : this.lexer.state.inRawBlock && this.rules.other.endPreScriptTag.test(e[0]) && (this.lexer.state.inRawBlock = !1), { type: "html", raw: e[0], inLink: this.lexer.state.inLink, inRawBlock: this.lexer.state.inRawBlock, block: !1, text: e[0] };
  }
  link(n) {
    let e = this.rules.inline.link.exec(n);
    if (e) {
      let t = e[2].trim();
      if (!this.options.pedantic && this.rules.other.startAngleBracket.test(t)) {
        if (!this.rules.other.endAngleBracket.test(t)) return;
        let a = st(t.slice(0, -1), "\\");
        if ((t.length - a.length) % 2 === 0) return;
      } else {
        let a = sa(e[2], "()");
        if (a === -2) return;
        if (a > -1) {
          let o = (e[0].indexOf("!") === 0 ? 5 : 4) + e[1].length + a;
          e[2] = e[2].substring(0, a), e[0] = e[0].substring(0, o).trim(), e[3] = "";
        }
      }
      let r = e[2], s = "";
      if (this.options.pedantic) {
        let a = this.rules.other.pedanticHrefTitle.exec(r);
        a && (r = a[1], s = a[3]);
      } else s = e[3] ? e[3].slice(1, -1) : "";
      return r = r.trim(), this.rules.other.startAngleBracket.test(r) && (this.options.pedantic && !this.rules.other.endAngleBracket.test(t) ? r = r.slice(1) : r = r.slice(1, -1)), nr(e, { href: r && r.replace(this.rules.inline.anyPunctuation, "$1"), title: s && s.replace(this.rules.inline.anyPunctuation, "$1") }, e[0], this.lexer, this.rules);
    }
  }
  reflink(n, e) {
    let t;
    if ((t = this.rules.inline.reflink.exec(n)) || (t = this.rules.inline.nolink.exec(n))) {
      let r = (t[2] || t[1]).replace(this.rules.other.multipleSpaceGlobal, " "), s = e[r.toLowerCase()];
      if (!s) {
        let a = t[0].charAt(0);
        return { type: "text", raw: a, text: a };
      }
      return nr(t, s, t[0], this.lexer, this.rules);
    }
  }
  emStrong(n, e, t = "") {
    let r = this.rules.inline.emStrongLDelim.exec(n);
    if (!(!r || r[3] && t.match(this.rules.other.unicodeAlphaNumeric)) && (!(r[1] || r[2]) || !t || this.rules.inline.punctuation.exec(t))) {
      let s = [...r[0]].length - 1, a, o, u = s, c = 0, m = r[0][0] === "*" ? this.rules.inline.emStrongRDelimAst : this.rules.inline.emStrongRDelimUnd;
      for (m.lastIndex = 0, e = e.slice(-1 * n.length + s); (r = m.exec(e)) != null; ) {
        if (a = r[1] || r[2] || r[3] || r[4] || r[5] || r[6], !a) continue;
        if (o = [...a].length, r[3] || r[4]) {
          u += o;
          continue;
        } else if ((r[5] || r[6]) && s % 3 && !((s + o) % 3)) {
          c += o;
          continue;
        }
        if (u -= o, u > 0) continue;
        o = Math.min(o, o + u + c);
        let g = [...r[0]][0].length, f = n.slice(0, s + r.index + g + o);
        if (Math.min(s, o) % 2) {
          let y = f.slice(1, -1);
          return { type: "em", raw: f, text: y, tokens: this.lexer.inlineTokens(y) };
        }
        let b = f.slice(2, -2);
        return { type: "strong", raw: f, text: b, tokens: this.lexer.inlineTokens(b) };
      }
    }
  }
  codespan(n) {
    let e = this.rules.inline.code.exec(n);
    if (e) {
      let t = e[2].replace(this.rules.other.newLineCharGlobal, " "), r = this.rules.other.nonSpaceChar.test(t), s = this.rules.other.startingSpaceChar.test(t) && this.rules.other.endingSpaceChar.test(t);
      return r && s && (t = t.substring(1, t.length - 1)), { type: "codespan", raw: e[0], text: t };
    }
  }
  br(n) {
    let e = this.rules.inline.br.exec(n);
    if (e) return { type: "br", raw: e[0] };
  }
  del(n) {
    let e = this.rules.inline.del.exec(n);
    if (e) return { type: "del", raw: e[0], text: e[2], tokens: this.lexer.inlineTokens(e[2]) };
  }
  autolink(n) {
    let e = this.rules.inline.autolink.exec(n);
    if (e) {
      let t, r;
      return e[2] === "@" ? (t = e[1], r = "mailto:" + t) : (t = e[1], r = t), { type: "link", raw: e[0], text: t, href: r, tokens: [{ type: "text", raw: t, text: t }] };
    }
  }
  url(n) {
    let e;
    if (e = this.rules.inline.url.exec(n)) {
      let t, r;
      if (e[2] === "@") t = e[0], r = "mailto:" + t;
      else {
        let s;
        do
          s = e[0], e[0] = this.rules.inline._backpedal.exec(e[0])?.[0] ?? "";
        while (s !== e[0]);
        t = e[0], e[1] === "www." ? r = "http://" + e[0] : r = e[0];
      }
      return { type: "link", raw: e[0], text: t, href: r, tokens: [{ type: "text", raw: t, text: t }] };
    }
  }
  inlineText(n) {
    let e = this.rules.inline.text.exec(n);
    if (e) {
      let t = this.lexer.state.inRawBlock;
      return { type: "text", raw: e[0], text: e[0], escaped: t };
    }
  }
}, J = class $n {
  tokens;
  options;
  state;
  tokenizer;
  inlineQueue;
  constructor(e) {
    this.tokens = [], this.tokens.links = /* @__PURE__ */ Object.create(null), this.options = e || Re, this.options.tokenizer = this.options.tokenizer || new Et(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = { inLink: !1, inRawBlock: !1, top: !0 };
    let t = { other: F, block: wt.normal, inline: nt.normal };
    this.options.pedantic ? (t.block = wt.pedantic, t.inline = nt.pedantic) : this.options.gfm && (t.block = wt.gfm, this.options.breaks ? t.inline = nt.breaks : t.inline = nt.gfm), this.tokenizer.rules = t;
  }
  static get rules() {
    return { block: wt, inline: nt };
  }
  static lex(e, t) {
    return new $n(t).lex(e);
  }
  static lexInline(e, t) {
    return new $n(t).inlineTokens(e);
  }
  lex(e) {
    e = e.replace(F.carriageReturn, `
`), this.blockTokens(e, this.tokens);
    for (let t = 0; t < this.inlineQueue.length; t++) {
      let r = this.inlineQueue[t];
      this.inlineTokens(r.src, r.tokens);
    }
    return this.inlineQueue = [], this.tokens;
  }
  blockTokens(e, t = [], r = !1) {
    for (this.options.pedantic && (e = e.replace(F.tabCharGlobal, "    ").replace(F.spaceLine, "")); e; ) {
      let s;
      if (this.options.extensions?.block?.some((o) => (s = o.call({ lexer: this }, e, t)) ? (e = e.substring(s.raw.length), t.push(s), !0) : !1)) continue;
      if (s = this.tokenizer.space(e)) {
        e = e.substring(s.raw.length);
        let o = t.at(-1);
        s.raw.length === 1 && o !== void 0 ? o.raw += `
` : t.push(s);
        continue;
      }
      if (s = this.tokenizer.code(e)) {
        e = e.substring(s.raw.length);
        let o = t.at(-1);
        o?.type === "paragraph" || o?.type === "text" ? (o.raw += (o.raw.endsWith(`
`) ? "" : `
`) + s.raw, o.text += `
` + s.text, this.inlineQueue.at(-1).src = o.text) : t.push(s);
        continue;
      }
      if (s = this.tokenizer.fences(e)) {
        e = e.substring(s.raw.length), t.push(s);
        continue;
      }
      if (s = this.tokenizer.heading(e)) {
        e = e.substring(s.raw.length), t.push(s);
        continue;
      }
      if (s = this.tokenizer.hr(e)) {
        e = e.substring(s.raw.length), t.push(s);
        continue;
      }
      if (s = this.tokenizer.blockquote(e)) {
        e = e.substring(s.raw.length), t.push(s);
        continue;
      }
      if (s = this.tokenizer.list(e)) {
        e = e.substring(s.raw.length), t.push(s);
        continue;
      }
      if (s = this.tokenizer.html(e)) {
        e = e.substring(s.raw.length), t.push(s);
        continue;
      }
      if (s = this.tokenizer.def(e)) {
        e = e.substring(s.raw.length);
        let o = t.at(-1);
        o?.type === "paragraph" || o?.type === "text" ? (o.raw += (o.raw.endsWith(`
`) ? "" : `
`) + s.raw, o.text += `
` + s.raw, this.inlineQueue.at(-1).src = o.text) : this.tokens.links[s.tag] || (this.tokens.links[s.tag] = { href: s.href, title: s.title }, t.push(s));
        continue;
      }
      if (s = this.tokenizer.table(e)) {
        e = e.substring(s.raw.length), t.push(s);
        continue;
      }
      if (s = this.tokenizer.lheading(e)) {
        e = e.substring(s.raw.length), t.push(s);
        continue;
      }
      let a = e;
      if (this.options.extensions?.startBlock) {
        let o = 1 / 0, u = e.slice(1), c;
        this.options.extensions.startBlock.forEach((m) => {
          c = m.call({ lexer: this }, u), typeof c == "number" && c >= 0 && (o = Math.min(o, c));
        }), o < 1 / 0 && o >= 0 && (a = e.substring(0, o + 1));
      }
      if (this.state.top && (s = this.tokenizer.paragraph(a))) {
        let o = t.at(-1);
        r && o?.type === "paragraph" ? (o.raw += (o.raw.endsWith(`
`) ? "" : `
`) + s.raw, o.text += `
` + s.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = o.text) : t.push(s), r = a.length !== e.length, e = e.substring(s.raw.length);
        continue;
      }
      if (s = this.tokenizer.text(e)) {
        e = e.substring(s.raw.length);
        let o = t.at(-1);
        o?.type === "text" ? (o.raw += (o.raw.endsWith(`
`) ? "" : `
`) + s.raw, o.text += `
` + s.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = o.text) : t.push(s);
        continue;
      }
      if (e) {
        let o = "Infinite loop on byte: " + e.charCodeAt(0);
        if (this.options.silent) {
          console.error(o);
          break;
        } else throw new Error(o);
      }
    }
    return this.state.top = !0, t;
  }
  inline(e, t = []) {
    return this.inlineQueue.push({ src: e, tokens: t }), t;
  }
  inlineTokens(e, t = []) {
    let r = e, s = null;
    if (this.tokens.links) {
      let c = Object.keys(this.tokens.links);
      if (c.length > 0) for (; (s = this.tokenizer.rules.inline.reflinkSearch.exec(r)) != null; ) c.includes(s[0].slice(s[0].lastIndexOf("[") + 1, -1)) && (r = r.slice(0, s.index) + "[" + "a".repeat(s[0].length - 2) + "]" + r.slice(this.tokenizer.rules.inline.reflinkSearch.lastIndex));
    }
    for (; (s = this.tokenizer.rules.inline.anyPunctuation.exec(r)) != null; ) r = r.slice(0, s.index) + "++" + r.slice(this.tokenizer.rules.inline.anyPunctuation.lastIndex);
    let a;
    for (; (s = this.tokenizer.rules.inline.blockSkip.exec(r)) != null; ) a = s[2] ? s[2].length : 0, r = r.slice(0, s.index + a) + "[" + "a".repeat(s[0].length - a - 2) + "]" + r.slice(this.tokenizer.rules.inline.blockSkip.lastIndex);
    r = this.options.hooks?.emStrongMask?.call({ lexer: this }, r) ?? r;
    let o = !1, u = "";
    for (; e; ) {
      o || (u = ""), o = !1;
      let c;
      if (this.options.extensions?.inline?.some((g) => (c = g.call({ lexer: this }, e, t)) ? (e = e.substring(c.raw.length), t.push(c), !0) : !1)) continue;
      if (c = this.tokenizer.escape(e)) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      if (c = this.tokenizer.tag(e)) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      if (c = this.tokenizer.link(e)) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      if (c = this.tokenizer.reflink(e, this.tokens.links)) {
        e = e.substring(c.raw.length);
        let g = t.at(-1);
        c.type === "text" && g?.type === "text" ? (g.raw += c.raw, g.text += c.text) : t.push(c);
        continue;
      }
      if (c = this.tokenizer.emStrong(e, r, u)) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      if (c = this.tokenizer.codespan(e)) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      if (c = this.tokenizer.br(e)) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      if (c = this.tokenizer.del(e)) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      if (c = this.tokenizer.autolink(e)) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      if (!this.state.inLink && (c = this.tokenizer.url(e))) {
        e = e.substring(c.raw.length), t.push(c);
        continue;
      }
      let m = e;
      if (this.options.extensions?.startInline) {
        let g = 1 / 0, f = e.slice(1), b;
        this.options.extensions.startInline.forEach((y) => {
          b = y.call({ lexer: this }, f), typeof b == "number" && b >= 0 && (g = Math.min(g, b));
        }), g < 1 / 0 && g >= 0 && (m = e.substring(0, g + 1));
      }
      if (c = this.tokenizer.inlineText(m)) {
        e = e.substring(c.raw.length), c.raw.slice(-1) !== "_" && (u = c.raw.slice(-1)), o = !0;
        let g = t.at(-1);
        g?.type === "text" ? (g.raw += c.raw, g.text += c.text) : t.push(c);
        continue;
      }
      if (e) {
        let g = "Infinite loop on byte: " + e.charCodeAt(0);
        if (this.options.silent) {
          console.error(g);
          break;
        } else throw new Error(g);
      }
    }
    return t;
  }
}, Rt = class {
  options;
  parser;
  constructor(n) {
    this.options = n || Re;
  }
  space(n) {
    return "";
  }
  code({ text: n, lang: e, escaped: t }) {
    let r = (e || "").match(F.notSpaceStart)?.[0], s = n.replace(F.endingNewline, "") + `
`;
    return r ? '<pre><code class="language-' + oe(r) + '">' + (t ? s : oe(s, !0)) + `</code></pre>
` : "<pre><code>" + (t ? s : oe(s, !0)) + `</code></pre>
`;
  }
  blockquote({ tokens: n }) {
    return `<blockquote>
${this.parser.parse(n)}</blockquote>
`;
  }
  html({ text: n }) {
    return n;
  }
  def(n) {
    return "";
  }
  heading({ tokens: n, depth: e }) {
    return `<h${e}>${this.parser.parseInline(n)}</h${e}>
`;
  }
  hr(n) {
    return `<hr>
`;
  }
  list(n) {
    let e = n.ordered, t = n.start, r = "";
    for (let o = 0; o < n.items.length; o++) {
      let u = n.items[o];
      r += this.listitem(u);
    }
    let s = e ? "ol" : "ul", a = e && t !== 1 ? ' start="' + t + '"' : "";
    return "<" + s + a + `>
` + r + "</" + s + `>
`;
  }
  listitem(n) {
    let e = "";
    if (n.task) {
      let t = this.checkbox({ checked: !!n.checked });
      n.loose ? n.tokens[0]?.type === "paragraph" ? (n.tokens[0].text = t + " " + n.tokens[0].text, n.tokens[0].tokens && n.tokens[0].tokens.length > 0 && n.tokens[0].tokens[0].type === "text" && (n.tokens[0].tokens[0].text = t + " " + oe(n.tokens[0].tokens[0].text), n.tokens[0].tokens[0].escaped = !0)) : n.tokens.unshift({ type: "text", raw: t + " ", text: t + " ", escaped: !0 }) : e += t + " ";
    }
    return e += this.parser.parse(n.tokens, !!n.loose), `<li>${e}</li>
`;
  }
  checkbox({ checked: n }) {
    return "<input " + (n ? 'checked="" ' : "") + 'disabled="" type="checkbox">';
  }
  paragraph({ tokens: n }) {
    return `<p>${this.parser.parseInline(n)}</p>
`;
  }
  table(n) {
    let e = "", t = "";
    for (let s = 0; s < n.header.length; s++) t += this.tablecell(n.header[s]);
    e += this.tablerow({ text: t });
    let r = "";
    for (let s = 0; s < n.rows.length; s++) {
      let a = n.rows[s];
      t = "";
      for (let o = 0; o < a.length; o++) t += this.tablecell(a[o]);
      r += this.tablerow({ text: t });
    }
    return r && (r = `<tbody>${r}</tbody>`), `<table>
<thead>
` + e + `</thead>
` + r + `</table>
`;
  }
  tablerow({ text: n }) {
    return `<tr>
${n}</tr>
`;
  }
  tablecell(n) {
    let e = this.parser.parseInline(n.tokens), t = n.header ? "th" : "td";
    return (n.align ? `<${t} align="${n.align}">` : `<${t}>`) + e + `</${t}>
`;
  }
  strong({ tokens: n }) {
    return `<strong>${this.parser.parseInline(n)}</strong>`;
  }
  em({ tokens: n }) {
    return `<em>${this.parser.parseInline(n)}</em>`;
  }
  codespan({ text: n }) {
    return `<code>${oe(n, !0)}</code>`;
  }
  br(n) {
    return "<br>";
  }
  del({ tokens: n }) {
    return `<del>${this.parser.parseInline(n)}</del>`;
  }
  link({ href: n, title: e, tokens: t }) {
    let r = this.parser.parseInline(t), s = er(n);
    if (s === null) return r;
    n = s;
    let a = '<a href="' + n + '"';
    return e && (a += ' title="' + oe(e) + '"'), a += ">" + r + "</a>", a;
  }
  image({ href: n, title: e, text: t, tokens: r }) {
    r && (t = this.parser.parseInline(r, this.parser.textRenderer));
    let s = er(n);
    if (s === null) return oe(t);
    n = s;
    let a = `<img src="${n}" alt="${t}"`;
    return e && (a += ` title="${oe(e)}"`), a += ">", a;
  }
  text(n) {
    return "tokens" in n && n.tokens ? this.parser.parseInline(n.tokens) : "escaped" in n && n.escaped ? n.text : oe(n.text);
  }
}, Fn = class {
  strong({ text: n }) {
    return n;
  }
  em({ text: n }) {
    return n;
  }
  codespan({ text: n }) {
    return n;
  }
  del({ text: n }) {
    return n;
  }
  html({ text: n }) {
    return n;
  }
  text({ text: n }) {
    return n;
  }
  link({ text: n }) {
    return "" + n;
  }
  image({ text: n }) {
    return "" + n;
  }
  br() {
    return "";
  }
}, ee = class Tn {
  options;
  renderer;
  textRenderer;
  constructor(e) {
    this.options = e || Re, this.options.renderer = this.options.renderer || new Rt(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new Fn();
  }
  static parse(e, t) {
    return new Tn(t).parse(e);
  }
  static parseInline(e, t) {
    return new Tn(t).parseInline(e);
  }
  parse(e, t = !0) {
    let r = "";
    for (let s = 0; s < e.length; s++) {
      let a = e[s];
      if (this.options.extensions?.renderers?.[a.type]) {
        let u = a, c = this.options.extensions.renderers[u.type].call({ parser: this }, u);
        if (c !== !1 || !["space", "hr", "heading", "code", "table", "blockquote", "list", "html", "def", "paragraph", "text"].includes(u.type)) {
          r += c || "";
          continue;
        }
      }
      let o = a;
      switch (o.type) {
        case "space": {
          r += this.renderer.space(o);
          continue;
        }
        case "hr": {
          r += this.renderer.hr(o);
          continue;
        }
        case "heading": {
          r += this.renderer.heading(o);
          continue;
        }
        case "code": {
          r += this.renderer.code(o);
          continue;
        }
        case "table": {
          r += this.renderer.table(o);
          continue;
        }
        case "blockquote": {
          r += this.renderer.blockquote(o);
          continue;
        }
        case "list": {
          r += this.renderer.list(o);
          continue;
        }
        case "html": {
          r += this.renderer.html(o);
          continue;
        }
        case "def": {
          r += this.renderer.def(o);
          continue;
        }
        case "paragraph": {
          r += this.renderer.paragraph(o);
          continue;
        }
        case "text": {
          let u = o, c = this.renderer.text(u);
          for (; s + 1 < e.length && e[s + 1].type === "text"; ) u = e[++s], c += `
` + this.renderer.text(u);
          t ? r += this.renderer.paragraph({ type: "paragraph", raw: c, text: c, tokens: [{ type: "text", raw: c, text: c, escaped: !0 }] }) : r += c;
          continue;
        }
        default: {
          let u = 'Token with "' + o.type + '" type was not found.';
          if (this.options.silent) return console.error(u), "";
          throw new Error(u);
        }
      }
    }
    return r;
  }
  parseInline(e, t = this.renderer) {
    let r = "";
    for (let s = 0; s < e.length; s++) {
      let a = e[s];
      if (this.options.extensions?.renderers?.[a.type]) {
        let u = this.options.extensions.renderers[a.type].call({ parser: this }, a);
        if (u !== !1 || !["escape", "html", "link", "image", "strong", "em", "codespan", "br", "del", "text"].includes(a.type)) {
          r += u || "";
          continue;
        }
      }
      let o = a;
      switch (o.type) {
        case "escape": {
          r += t.text(o);
          break;
        }
        case "html": {
          r += t.html(o);
          break;
        }
        case "link": {
          r += t.link(o);
          break;
        }
        case "image": {
          r += t.image(o);
          break;
        }
        case "strong": {
          r += t.strong(o);
          break;
        }
        case "em": {
          r += t.em(o);
          break;
        }
        case "codespan": {
          r += t.codespan(o);
          break;
        }
        case "br": {
          r += t.br(o);
          break;
        }
        case "del": {
          r += t.del(o);
          break;
        }
        case "text": {
          r += t.text(o);
          break;
        }
        default: {
          let u = 'Token with "' + o.type + '" type was not found.';
          if (this.options.silent) return console.error(u), "";
          throw new Error(u);
        }
      }
    }
    return r;
  }
}, rt = class {
  options;
  block;
  constructor(n) {
    this.options = n || Re;
  }
  static passThroughHooks = /* @__PURE__ */ new Set(["preprocess", "postprocess", "processAllTokens", "emStrongMask"]);
  static passThroughHooksRespectAsync = /* @__PURE__ */ new Set(["preprocess", "postprocess", "processAllTokens"]);
  preprocess(n) {
    return n;
  }
  postprocess(n) {
    return n;
  }
  processAllTokens(n) {
    return n;
  }
  emStrongMask(n) {
    return n;
  }
  provideLexer() {
    return this.block ? J.lex : J.lexInline;
  }
  provideParser() {
    return this.block ? ee.parse : ee.parseInline;
  }
}, Pr = class {
  defaults = Ln();
  options = this.setOptions;
  parse = this.parseMarkdown(!0);
  parseInline = this.parseMarkdown(!1);
  Parser = ee;
  Renderer = Rt;
  TextRenderer = Fn;
  Lexer = J;
  Tokenizer = Et;
  Hooks = rt;
  constructor(...n) {
    this.use(...n);
  }
  walkTokens(n, e) {
    let t = [];
    for (let r of n) switch (t = t.concat(e.call(this, r)), r.type) {
      case "table": {
        let s = r;
        for (let a of s.header) t = t.concat(this.walkTokens(a.tokens, e));
        for (let a of s.rows) for (let o of a) t = t.concat(this.walkTokens(o.tokens, e));
        break;
      }
      case "list": {
        let s = r;
        t = t.concat(this.walkTokens(s.items, e));
        break;
      }
      default: {
        let s = r;
        this.defaults.extensions?.childTokens?.[s.type] ? this.defaults.extensions.childTokens[s.type].forEach((a) => {
          let o = s[a].flat(1 / 0);
          t = t.concat(this.walkTokens(o, e));
        }) : s.tokens && (t = t.concat(this.walkTokens(s.tokens, e)));
      }
    }
    return t;
  }
  use(...n) {
    let e = this.defaults.extensions || { renderers: {}, childTokens: {} };
    return n.forEach((t) => {
      let r = { ...t };
      if (r.async = this.defaults.async || r.async || !1, t.extensions && (t.extensions.forEach((s) => {
        if (!s.name) throw new Error("extension name required");
        if ("renderer" in s) {
          let a = e.renderers[s.name];
          a ? e.renderers[s.name] = function(...o) {
            let u = s.renderer.apply(this, o);
            return u === !1 && (u = a.apply(this, o)), u;
          } : e.renderers[s.name] = s.renderer;
        }
        if ("tokenizer" in s) {
          if (!s.level || s.level !== "block" && s.level !== "inline") throw new Error("extension level must be 'block' or 'inline'");
          let a = e[s.level];
          a ? a.unshift(s.tokenizer) : e[s.level] = [s.tokenizer], s.start && (s.level === "block" ? e.startBlock ? e.startBlock.push(s.start) : e.startBlock = [s.start] : s.level === "inline" && (e.startInline ? e.startInline.push(s.start) : e.startInline = [s.start]));
        }
        "childTokens" in s && s.childTokens && (e.childTokens[s.name] = s.childTokens);
      }), r.extensions = e), t.renderer) {
        let s = this.defaults.renderer || new Rt(this.defaults);
        for (let a in t.renderer) {
          if (!(a in s)) throw new Error(`renderer '${a}' does not exist`);
          if (["options", "parser"].includes(a)) continue;
          let o = a, u = t.renderer[o], c = s[o];
          s[o] = (...m) => {
            let g = u.apply(s, m);
            return g === !1 && (g = c.apply(s, m)), g || "";
          };
        }
        r.renderer = s;
      }
      if (t.tokenizer) {
        let s = this.defaults.tokenizer || new Et(this.defaults);
        for (let a in t.tokenizer) {
          if (!(a in s)) throw new Error(`tokenizer '${a}' does not exist`);
          if (["options", "rules", "lexer"].includes(a)) continue;
          let o = a, u = t.tokenizer[o], c = s[o];
          s[o] = (...m) => {
            let g = u.apply(s, m);
            return g === !1 && (g = c.apply(s, m)), g;
          };
        }
        r.tokenizer = s;
      }
      if (t.hooks) {
        let s = this.defaults.hooks || new rt();
        for (let a in t.hooks) {
          if (!(a in s)) throw new Error(`hook '${a}' does not exist`);
          if (["options", "block"].includes(a)) continue;
          let o = a, u = t.hooks[o], c = s[o];
          rt.passThroughHooks.has(a) ? s[o] = (m) => {
            if (this.defaults.async && rt.passThroughHooksRespectAsync.has(a)) return (async () => {
              let f = await u.call(s, m);
              return c.call(s, f);
            })();
            let g = u.call(s, m);
            return c.call(s, g);
          } : s[o] = (...m) => {
            if (this.defaults.async) return (async () => {
              let f = await u.apply(s, m);
              return f === !1 && (f = await c.apply(s, m)), f;
            })();
            let g = u.apply(s, m);
            return g === !1 && (g = c.apply(s, m)), g;
          };
        }
        r.hooks = s;
      }
      if (t.walkTokens) {
        let s = this.defaults.walkTokens, a = t.walkTokens;
        r.walkTokens = function(o) {
          let u = [];
          return u.push(a.call(this, o)), s && (u = u.concat(s.call(this, o))), u;
        };
      }
      this.defaults = { ...this.defaults, ...r };
    }), this;
  }
  setOptions(n) {
    return this.defaults = { ...this.defaults, ...n }, this;
  }
  lexer(n, e) {
    return J.lex(n, e ?? this.defaults);
  }
  parser(n, e) {
    return ee.parse(n, e ?? this.defaults);
  }
  parseMarkdown(n) {
    return (e, t) => {
      let r = { ...t }, s = { ...this.defaults, ...r }, a = this.onError(!!s.silent, !!s.async);
      if (this.defaults.async === !0 && r.async === !1) return a(new Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));
      if (typeof e > "u" || e === null) return a(new Error("marked(): input parameter is undefined or null"));
      if (typeof e != "string") return a(new Error("marked(): input parameter is of type " + Object.prototype.toString.call(e) + ", string expected"));
      if (s.hooks && (s.hooks.options = s, s.hooks.block = n), s.async) return (async () => {
        let o = s.hooks ? await s.hooks.preprocess(e) : e, u = await (s.hooks ? await s.hooks.provideLexer() : n ? J.lex : J.lexInline)(o, s), c = s.hooks ? await s.hooks.processAllTokens(u) : u;
        s.walkTokens && await Promise.all(this.walkTokens(c, s.walkTokens));
        let m = await (s.hooks ? await s.hooks.provideParser() : n ? ee.parse : ee.parseInline)(c, s);
        return s.hooks ? await s.hooks.postprocess(m) : m;
      })().catch(a);
      try {
        s.hooks && (e = s.hooks.preprocess(e));
        let o = (s.hooks ? s.hooks.provideLexer() : n ? J.lex : J.lexInline)(e, s);
        s.hooks && (o = s.hooks.processAllTokens(o)), s.walkTokens && this.walkTokens(o, s.walkTokens);
        let u = (s.hooks ? s.hooks.provideParser() : n ? ee.parse : ee.parseInline)(o, s);
        return s.hooks && (u = s.hooks.postprocess(u)), u;
      } catch (o) {
        return a(o);
      }
    };
  }
  onError(n, e) {
    return (t) => {
      if (t.message += `
Please report this to https://github.com/markedjs/marked.`, n) {
        let r = "<p>An error occurred:</p><pre>" + oe(t.message + "", !0) + "</pre>";
        return e ? Promise.resolve(r) : r;
      }
      if (e) return Promise.reject(t);
      throw t;
    };
  }
}, Ee = new Pr();
function T(n, e) {
  return Ee.parse(n, e);
}
T.options = T.setOptions = function(n) {
  return Ee.setOptions(n), T.defaults = Ee.defaults, wr(T.defaults), T;
};
T.getDefaults = Ln;
T.defaults = Re;
T.use = function(...n) {
  return Ee.use(...n), T.defaults = Ee.defaults, wr(T.defaults), T;
};
T.walkTokens = function(n, e) {
  return Ee.walkTokens(n, e);
};
T.parseInline = Ee.parseInline;
T.Parser = ee;
T.parser = ee.parse;
T.Renderer = Rt;
T.TextRenderer = Fn;
T.Lexer = J;
T.lexer = J.lex;
T.Tokenizer = Et;
T.Hooks = rt;
T.parse = T;
T.options;
T.setOptions;
T.use;
T.walkTokens;
T.parseInline;
ee.parse;
J.lex;
const ia = new Pr({ gfm: !0, breaks: !0, async: !1 });
kr.addHook("afterSanitizeAttributes", (n) => {
  n.tagName === "A" && (n.setAttribute("target", "_blank"), n.setAttribute("rel", "noopener noreferrer"));
});
const At = /* @__PURE__ */ new Map();
function oa(n, e = !0) {
  if (e) {
    const r = At.get(n);
    if (r !== void 0) return r;
  }
  const t = kr.sanitize(ia.parse(n), {
    FORBID_TAGS: ["style", "form", "input", "button", "iframe", "img"],
    FORBID_ATTR: ["style"]
  });
  return e && (At.size > 300 && At.clear(), At.set(n, t)), t;
}
const aa = di`
  :host {
    display: block;
    height: 100%;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif);
    --radius: 12px;
    --line: var(--divider-color, rgba(127, 127, 127, 0.25));
    --card: var(--card-background-color, #fff);
    --accent: var(--primary-color, #03a9f4);
    --muted: var(--secondary-text-color, #777);
    --danger: var(--error-color, #db4437);
    --ok: var(--success-color, #43a047);
    --warn: var(--warning-color, #ffa600);
  }
  .layout {
    display: flex;
    height: 100%;
  }
  nav {
    width: 260px;
    flex: none;
    border-right: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    padding: 12px;
    gap: 8px;
    box-sizing: border-box;
    background: var(--sidebar-background-color, var(--card));
  }
  .narrow nav {
    position: absolute;
    z-index: 3;
    top: 56px;
    bottom: 0;
    left: 0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  }
  .convs {
    overflow-y: auto;
    flex: 1;
  }
  .conv {
    display: flex;
    align-items: center;
    padding: 8px 10px;
    border-radius: 8px;
    cursor: pointer;
    gap: 4px;
  }
  .conv:hover,
  .conv.active {
    background: rgba(127, 127, 127, 0.12);
  }
  .conv-title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 14px;
  }
  .conv .icon {
    visibility: hidden;
  }
  .conv:hover .icon {
    visibility: visible;
  }
  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  header {
    height: 56px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 12px;
    border-bottom: 1px solid var(--line);
    flex: none;
  }
  .title {
    flex: 1;
    font-size: 18px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px max(16px, calc((100% - 820px) / 2));
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .msg {
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  .msg.user {
    align-self: flex-end;
    background: var(--accent);
    color: var(--text-primary-color, #fff);
    padding: 8px 14px;
    border-radius: var(--radius) var(--radius) 4px var(--radius);
    max-width: 80%;
    white-space: pre-wrap;
  }
  .md :first-child {
    margin-top: 0;
  }
  .md :last-child {
    margin-bottom: 0;
  }
  .md pre,
  pre {
    background: rgba(127, 127, 127, 0.1);
    padding: 8px 10px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 12.5px;
    margin: 6px 0;
    white-space: pre;
  }
  .md code {
    font-size: 0.92em;
  }
  .md table {
    border-collapse: collapse;
  }
  .md td,
  .md th {
    border: 1px solid var(--line);
    padding: 4px 8px;
  }
  .md a {
    color: var(--accent);
  }
  .typing span {
    display: inline-block;
    width: 6px;
    height: 6px;
    margin-right: 4px;
    border-radius: 50%;
    background: var(--muted);
    animation: blink 1.2s infinite;
  }
  .typing span:nth-child(2) {
    animation-delay: 0.2s;
  }
  .typing span:nth-child(3) {
    animation-delay: 0.4s;
  }
  @keyframes blink {
    50% {
      opacity: 0.2;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .typing span {
      animation: none;
    }
  }
  .tool {
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--card);
    font-size: 13.5px;
    position: relative;
  }
  .tool.waiting {
    border-color: var(--accent);
  }
  .tool.waiting.risky {
    border-color: var(--warn);
  }
  .tool summary {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    cursor: pointer;
    list-style: none;
  }
  .tool summary::-webkit-details-marker {
    display: none;
  }
  .tool details > :not(summary) {
    margin: 0 10px 8px;
  }
  .badge {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    flex: none;
    background: rgba(127, 127, 127, 0.18);
  }
  .ok .badge {
    background: var(--ok);
    color: #fff;
  }
  .error .badge {
    background: var(--danger);
    color: #fff;
  }
  .tool-name {
    font-weight: 500;
    flex: none;
  }
  .tool-summary {
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }
  .tag {
    font-size: 11px;
    color: var(--muted);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0 6px;
  }
  .diff .add {
    color: var(--ok);
  }
  .diff .del {
    color: var(--danger);
  }
  .diff .hunk {
    color: var(--muted);
  }
  pre.result,
  pre.args {
    max-height: 240px;
    overflow: auto;
    white-space: pre-wrap;
  }
  .approval {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    padding: 0 10px 10px;
  }
  .approval .reason {
    width: 100%;
    font-size: 13px;
  }
  .approval input {
    flex: 1;
    min-width: 140px;
  }
  .undo {
    position: absolute;
    right: 8px;
    top: 6px;
  }
  .notice {
    font-size: 13px;
    color: var(--muted);
    text-align: center;
  }
  .notice.error {
    color: var(--danger);
  }
  .welcome {
    margin: auto 0;
    text-align: center;
    color: var(--muted);
  }
  .welcome h2 {
    color: var(--primary-text-color);
    font-weight: 500;
  }
  .tips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 16px;
  }
  .tip {
    border: 1px solid var(--line);
    background: var(--card);
    color: var(--primary-text-color);
    border-radius: 18px;
    padding: 8px 14px;
    cursor: pointer;
    font: inherit;
    font-size: 13.5px;
  }
  footer {
    padding: 8px max(16px, calc((100% - 820px) / 2)) 12px;
    flex: none;
  }
  .composer {
    display: flex;
    gap: 8px;
    align-items: flex-end;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 8px;
    background: var(--card);
  }
  textarea {
    flex: 1;
    border: none;
    resize: none;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 15px;
    outline: none;
    max-height: 240px;
    padding: 6px;
  }
  .meta {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 6px;
    font-size: 12.5px;
    color: var(--muted);
    flex-wrap: wrap;
  }
  .usage {
    margin-left: auto;
    white-space: nowrap;
  }
  select,
  input {
    background: var(--card);
    color: inherit;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 4px 6px;
    font: inherit;
  }
  input.model {
    width: 200px;
  }
  button {
    font: inherit;
    cursor: pointer;
    border-radius: 8px;
    border: 1px solid transparent;
    padding: 6px 14px;
  }
  button.primary {
    background: var(--accent);
    color: var(--text-primary-color, #fff);
  }
  button.danger {
    background: var(--danger);
    color: #fff;
  }
  button.ghost {
    background: transparent;
    color: var(--primary-text-color);
    border-color: var(--line);
  }
  button.icon {
    background: transparent;
    color: var(--muted);
    padding: 4px 8px;
  }
  button.small {
    padding: 2px 8px;
    font-size: 12px;
  }
  button.wide {
    width: 100%;
  }
  button:focus-visible,
  .tip:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .empty {
    padding: 32px;
    color: var(--muted);
  }
`;
var la = Object.defineProperty, W = (n, e, t, r) => {
  for (var s = void 0, a = n.length - 1, o; a >= 0; a--)
    (o = n[a]) && (s = o(e, t, s) || s);
  return s && la(e, t, s), s;
};
const sr = { input: 0, output: 0, cache_read: 0, cache_write: 0, cost: 0 };
class H extends ot {
  constructor() {
    super(...arguments), this.narrow = !1, this.convs = [], this.convId = null, this.chatTitle = "New chat", this.items = [], this.usage = sr, this.running = !1, this.providerId = "", this.model = "", this.showList = !1, this.loadError = "", this.started = !1, this.stickToBottom = !0;
  }
  static {
    this.styles = aa;
  }
  get ws() {
    return this.hass.connection;
  }
  updated(e) {
    e.has("hass") && this.hass && !this.started && (this.started = !0, this.init()), this.stickToBottom && this.scroller && (this.scroller.scrollTop = this.scroller.scrollHeight);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this.detach(), this.started = !1;
  }
  async init() {
    try {
      this.info = await this.ws.sendMessagePromise({ type: "llm_agent/info" });
    } catch (t) {
      this.loadError = t.message ?? String(t);
      return;
    }
    const e = this.info.providers[0];
    e && !this.providerId && (this.providerId = e.id, this.model = e.default_model), await this.refreshList(), this.convId && await this.open(this.convId);
  }
  async refreshList() {
    this.convs = await this.ws.sendMessagePromise({
      type: "llm_agent/conversations/list"
    });
  }
  get provider() {
    return this.info?.providers.find((e) => e.id === this.providerId);
  }
  // ---- conversations -------------------------------------------------------
  async detach() {
    const e = this.unsub;
    if (this.unsub = void 0, e)
      try {
        await e();
      } catch {
      }
  }
  newChat() {
    this.detach(), this.convId = null, this.chatTitle = "New chat", this.items = [], this.usage = sr, this.running = !1, this.showList = !1;
    const e = this.provider ?? this.info?.providers[0];
    e && (this.model = e.default_model), this.input?.focus();
  }
  async open(e) {
    await this.detach(), this.showList = !1;
    const t = await this.ws.sendMessagePromise({
      type: "llm_agent/conversations/get",
      conversation_id: e
    });
    this.convId = t.id, this.chatTitle = t.title, this.usage = t.usage, this.providerId = t.provider_id, this.model = t.model, this.items = ca(t.messages), this.running = !1, this.stickToBottom = !0, (await this.ws.sendMessagePromise({ type: "llm_agent/info" })).running.includes(e) && (this.running = !0, this.items = [...this.items, { kind: "assistant", text: "" }], this.unsub = await this.ws.subscribeMessage((s) => this.onEvent(s), {
      type: "llm_agent/attach",
      conversation_id: e
    }));
  }
  async removeConv(e, t) {
    t.stopPropagation(), confirm("Delete this conversation?") && (await this.ws.sendMessagePromise({ type: "llm_agent/conversations/delete", conversation_id: e }), e === this.convId && this.newChat(), await this.refreshList());
  }
  // ---- sending -------------------------------------------------------------
  async send() {
    const e = this.input?.value.trim();
    if (!(!e || this.running)) {
      this.input.value = "", this.autosize(), this.items = [...this.items, { kind: "user", text: e }, { kind: "assistant", text: "" }], this.running = !0, this.stickToBottom = !0;
      try {
        let t = !0;
        this.unsub = await this.ws.subscribeMessage(
          (r) => {
            t && "conversation_id" in r || (t = !1, this.onEvent(r));
          },
          {
            type: "llm_agent/chat",
            text: e,
            conversation_id: this.convId,
            provider_id: this.providerId || void 0,
            model: this.model || void 0
          }
        );
      } catch (t) {
        this.running = !1, this.push({ kind: "notice", text: yn(t), error: !0 });
        return;
      }
      this.convId || (await this.refreshList(), this.convId = this.convs[0]?.id ?? null, this.chatTitle = this.convs[0]?.title ?? e.slice(0, 60));
    }
  }
  onEvent(e) {
    switch (e.type) {
      case "delta": {
        const t = this.items[this.items.length - 1];
        t?.kind === "assistant" ? t.text += e.text : this.items.push({ kind: "assistant", text: e.text }), this.scheduleRender();
        return;
      }
      case "tool_start":
        this.push({ kind: "tool", id: e.call_id, name: e.name, args: e.args, status: "running" });
        return;
      case "approval":
        this.patchTool(e.call_id, {
          status: "waiting",
          approval: { summary: e.summary, reason: e.reason, risky: e.risky, diff: e.diff }
        }, { kind: "tool", id: e.call_id, name: e.name, args: e.args, status: "waiting" });
        return;
      case "tool_result":
        this.patchTool(e.call_id, {
          status: e.ok ? "ok" : "error",
          summary: e.summary,
          preview: e.preview,
          snapshotId: e.snapshot_id,
          approval: void 0
        }), this.push({ kind: "assistant", text: "" });
        return;
      case "usage":
        this.usage = e.usage;
        return;
      case "notice":
        this.push({ kind: "notice", text: e.text });
        return;
      case "error":
        this.push({ kind: "notice", text: e.message, error: !0 });
        return;
      case "done":
        this.usage = e.usage, this.running = !1, this.items = this.items.filter((t) => !(t.kind === "assistant" && !t.text)), this.detach(), this.refreshList().then(() => {
          this.chatTitle = this.convs.find((t) => t.id === this.convId)?.title ?? this.chatTitle;
        });
        return;
    }
  }
  scheduleRender() {
    this.renderTimer === void 0 && (this.renderTimer = window.setTimeout(() => {
      this.renderTimer = void 0, this.requestUpdate();
    }, 80));
  }
  push(e) {
    const t = this.items.filter((r) => !(r.kind === "assistant" && !r.text));
    this.items = [...t, e];
  }
  patchTool(e, t, r) {
    let s = !1;
    this.items = this.items.map((a) => a.kind === "tool" && a.id === e ? (s = !0, { ...a, ...t }) : a), !s && r && this.push({ ...r, ...t });
  }
  async answer(e, t) {
    const r = this.renderRoot.querySelector(`#note-${CSS.escape(e)}`)?.value ?? "";
    this.patchTool(e, { status: "running", approval: void 0 });
    try {
      await this.ws.sendMessagePromise({
        type: "llm_agent/approve",
        conversation_id: this.convId,
        call_id: e,
        approved: t,
        note: r
      });
    } catch (s) {
      this.push({ kind: "notice", text: yn(s), error: !0 });
    }
  }
  async undo(e) {
    if (!(!e.snapshotId || !confirm(`Undo "${e.summary || e.name}"?`)))
      try {
        const t = await this.ws.sendMessagePromise({
          type: "llm_agent/undo",
          snapshot_id: e.snapshotId
        });
        this.patchTool(e.id, { undone: !0 }), this.push({ kind: "notice", text: `Undone: ${t.summary}` });
      } catch (t) {
        this.push({ kind: "notice", text: yn(t), error: !0 });
      }
  }
  async stop() {
    this.convId && await this.ws.sendMessagePromise({ type: "llm_agent/cancel", conversation_id: this.convId });
  }
  // ---- input ---------------------------------------------------------------
  onKey(e) {
    e.key === "Enter" && !e.shiftKey && !e.isComposing && (e.preventDefault(), this.send());
  }
  autosize() {
    const e = this.input;
    e && (e.style.height = "auto", e.style.height = `${Math.min(e.scrollHeight, 240)}px`);
  }
  onScroll() {
    const e = this.scroller;
    e && (this.stickToBottom = e.scrollHeight - e.scrollTop - e.clientHeight < 40);
  }
  pickProvider(e) {
    this.providerId = e.target.value, this.model = this.provider?.default_model ?? "";
  }
  // ---- render --------------------------------------------------------------
  render() {
    if (this.loadError)
      return S`<div class="empty">LLM Agent could not load: ${this.loadError}</div>`;
    if (this.info && !this.info.providers.length)
      return S`<div class="empty">
        No AI provider is configured. Add one under Settings → Devices &amp; services → LLM Agent →
        Configure.
      </div>`;
    const e = !this.narrow || this.showList;
    return S`
      <div class="layout ${this.narrow ? "narrow" : ""}">
        ${e ? this.renderList() : $}
        <main>
          <header>
            <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
            ${this.narrow ? S`<button class="icon" title="Conversations" @click=${() => this.showList = !this.showList}>☰</button>` : $}
            <div class="title">${this.chatTitle}</div>
            <button class="ghost" @click=${this.newChat}>New chat</button>
          </header>
          <div class="messages" @scroll=${this.onScroll}>
            ${this.items.length ? $ : this.renderWelcome()}
            ${ji(
      this.items,
      (t, r) => r,
      (t, r) => this.renderItem(t, r === this.items.length - 1)
    )}
          </div>
          ${this.renderComposer()}
        </main>
      </div>
    `;
  }
  renderList() {
    return S`<nav>
      <button class="primary wide" @click=${this.newChat}>+ New chat</button>
      <div class="convs">
        ${this.convs.map(
      (e) => S`<div
            class="conv ${e.id === this.convId ? "active" : ""}"
            @click=${() => this.open(e.id)}
          >
            <span class="conv-title">${e.title}</span>
            <button class="icon small" title="Delete" @click=${(t) => this.removeConv(e.id, t)}>✕</button>
          </div>`
    )}
      </div>
    </nav>`;
  }
  renderWelcome() {
    const e = [
      "Turn off all the lights downstairs",
      "Make a dashboard for the living room",
      "Create an automation: porch light on at sunset, off at 11pm",
      "Why did the hallway sensor go unavailable yesterday?"
    ];
    return S`<div class="welcome">
      <h2>What should I do?</h2>
      <p>
        I can control devices, answer questions about your home, and build automations, scenes,
        scripts and dashboards. Mode: <b>${da(this.info?.approval_mode)}</b>.
      </p>
      <div class="tips">
        ${e.map(
      (t) => S`<button class="tip" @click=${() => {
        this.input.value = t, this.input.focus();
      }}>${t}</button>`
    )}
      </div>
    </div>`;
  }
  renderItem(e, t) {
    switch (e.kind) {
      case "user":
        return S`<div class="msg user">${e.text}</div>`;
      case "assistant":
        return e.text ? S`<div class="msg assistant md">
          ${Ui(oa(e.text, !(t && this.running)))}
        </div>` : t && this.running ? S`<div class="msg assistant typing"><span></span><span></span><span></span></div>` : $;
      case "notice":
        return S`<div class="notice ${e.error ? "error" : ""}">${e.text}</div>`;
      case "tool":
        return this.renderTool(e);
    }
  }
  renderTool(e) {
    const t = { running: "⋯", ok: "✓", error: "!", waiting: "?" }[e.status], r = e.approval;
    return S`<div class="tool ${e.status} ${r?.risky ? "risky" : ""}">
      <details ?open=${!!r}>
        <summary>
          <span class="badge">${t}</span>
          <span class="tool-name">${pa(e.name)}</span>
          <span class="tool-summary">${r?.summary ?? e.summary ?? ha(e.args)}</span>
          ${e.undone ? S`<span class="tag">undone</span>` : $}
        </summary>
        ${r?.diff ? S`<pre class="diff">${ua(r.diff)}</pre>` : $}
        ${r ? $ : S`<pre class="args">${JSON.stringify(e.args, null, 2)}</pre>`}
        ${e.preview && !r ? S`<pre class="result">${e.preview}</pre>` : $}
      </details>
      ${r ? S`<div class="approval">
            <div class="reason">${r.risky ? "⚠ " : ""}Needs your approval${r.reason ? `: ${r.reason}` : ""}</div>
            <input id="note-${e.id}" placeholder="Optional note for the AI" />
            <button class="danger" @click=${() => this.answer(e.id, !1)}>Deny</button>
            <button class="primary" @click=${() => this.answer(e.id, !0)}>Approve</button>
          </div>` : $}
      ${e.snapshotId && !e.undone && e.status === "ok" ? S`<button class="ghost small undo" @click=${() => this.undo(e)}>Undo</button>` : $}
    </div>`;
  }
  renderComposer() {
    const e = this.provider, t = "models";
    return S`<footer>
      <div class="composer">
        <textarea
          rows="1"
          placeholder="Ask or tell me to do something…"
          @keydown=${this.onKey}
          @input=${this.autosize}
        ></textarea>
        ${this.running ? S`<button class="danger" @click=${this.stop}>Stop</button>` : S`<button class="primary" @click=${this.send}>Send</button>`}
      </div>
      <div class="meta">
        <select @change=${this.pickProvider} .value=${this.providerId} ?disabled=${this.running}>
          ${this.info?.providers.map(
      (r) => S`<option value=${r.id} ?selected=${r.id === this.providerId}>${r.name}</option>`
    )}
        </select>
        <input
          class="model"
          list=${t}
          .value=${this.model}
          ?disabled=${this.running}
          @change=${(r) => this.model = r.target.value.trim()}
          title="Model id (pick or type)"
        />
        <datalist id=${t}>
          ${e?.models.map((r) => S`<option value=${r.id}>${r.label}</option>`)}
        </datalist>
        <span class="usage" title="Tokens in / out (cached). Cost is an estimate.">
          ${_n(this.usage.input + this.usage.cache_read + this.usage.cache_write)} in ·
          ${_n(this.usage.output)} out
          ${this.usage.cache_read ? S` · ${_n(this.usage.cache_read)} cached` : $}
          · ${this.usage.cost == null ? "cost n/a" : `~$${this.usage.cost.toFixed(this.usage.cost < 1 ? 4 : 2)}`}
        </span>
      </div>
    </footer>`;
  }
}
W([
  Pn({ attribute: !1 })
], H.prototype, "hass");
W([
  Pn({ type: Boolean })
], H.prototype, "narrow");
W([
  te()
], H.prototype, "info");
W([
  te()
], H.prototype, "convs");
W([
  te()
], H.prototype, "convId");
W([
  te()
], H.prototype, "chatTitle");
W([
  te()
], H.prototype, "items");
W([
  te()
], H.prototype, "usage");
W([
  te()
], H.prototype, "running");
W([
  te()
], H.prototype, "providerId");
W([
  te()
], H.prototype, "model");
W([
  te()
], H.prototype, "showList");
W([
  te()
], H.prototype, "loadError");
W([
  pr("textarea")
], H.prototype, "input");
W([
  pr(".messages")
], H.prototype, "scroller");
function ca(n) {
  const e = [], t = /* @__PURE__ */ new Map();
  for (const r of n)
    if (r.role === "user") e.push({ kind: "user", text: r.content });
    else if (r.role === "assistant") {
      r.content && e.push({ kind: "assistant", text: r.content });
      for (const s of r.tool_calls) t.set(s.id, { name: s.name, args: s.args });
    } else {
      const s = t.get(r.tool_call_id);
      e.push({
        kind: "tool",
        id: r.tool_call_id,
        name: r.name,
        args: s?.args ?? {},
        status: r.ok ? "ok" : "error",
        summary: r.summary || (r.decision === "denied" ? "Denied" : ""),
        preview: r.preview,
        snapshotId: r.snapshot_id
      });
    }
  return e;
}
function ua(n) {
  return n.split(`
`).map((e) => {
    const t = e.startsWith("+") && !e.startsWith("+++") ? "add" : e.startsWith("-") && !e.startsWith("---") ? "del" : e.startsWith("@@") ? "hunk" : "";
    return S`<span class=${t}>${e}\n</span>`;
  });
}
function pa(n) {
  return n.replace(/_/g, " ");
}
function ha(n) {
  const e = Object.entries(n).filter(([t]) => !t.startsWith("_")).map(([t, r]) => `${t}=${typeof r == "string" ? r : JSON.stringify(r)}`).join(" ");
  return e.length > 120 ? `${e.slice(0, 117)}…` : e;
}
function _n(n) {
  return n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : String(n);
}
function da(n) {
  return { ask_all: "ask before every change", ask_risky: "ask before risky actions", autopilot: "autopilot" }[n ?? ""] ?? "";
}
function yn(n) {
  return n.message ?? String(n);
}
customElements.get("llm-agent-panel") || customElements.define("llm-agent-panel", H);
