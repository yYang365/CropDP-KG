# Django Vue 模板 ✌️ 🐍

![Vue Logo](/src/assets/logo-vue.png "Vue Logo")
![Django Logo](/src/assets/logo-django.png "Django Logo")

这个模板是一个使用 Vue 和 Django 的最小示例应用。

在这个项目中，Vue 和 Django 被清晰地分离。Vue、Yarn 和 Webpack 负责所有前端逻辑和打包构建。Django 和 Django REST framework 用于管理数据模型、Web API 以及静态文件服务。

虽然也可以添加端点来提供 Django 渲染的 HTML 响应，但这里的设计意图是：主要将 Django 用作后端，而由 Vue + Vue Router 作为单页应用（SPA）处理视图渲染和路由。

开箱即用时，Django 会在 `/` 提供应用入口（`index.html` + 打包后的资源），在 `/api/` 提供数据，在 `/static/` 提供静态文件。Django 管理后台也可在 `/admin/` 使用，并可根据需要扩展。

Vue CLI `create` 和 Django `createproject` 的应用模板尽量保持与原始状态接近，只有在需要更好集成两个框架时，才进行必要配置调整。

#### 备选方案

如果这个设置不符合你的需求，你也可以看看其他类似项目：

* [ariera/django-vue-template](https://github.com/ariera/django-vue-template)
* [vchaptsev/cookiecutter-django-vue](https://github.com/vchaptsev/cookiecutter-django-vue)

更喜欢 Flask？可以看看 [gtalarico/flask-vuejs-template](https://github.com/gtalarico/flask-vuejs-template)

### 演示

[在线演示](https://django-vue-template-demo.herokuapp.com/)

### 包含内容

* Django
* Django REST framework
* Django Whitenoise，支持 CDN
* Vue CLI 3
* Vue Router
* Vuex
* Gunicorn
* Heroku 部署配置

### 模板结构

| 位置 | 内容 |
|------|------|
| `/backend` | Django 项目与后端配置 |
| `/backend/api` | Django 应用（`/api`） |
| `/src` | Vue 应用 |
| `/src/main.js` | JS 应用入口 |
| `/public/index.html` | [HTML 应用入口](https://cli.vuejs.org/guide/html-and-static-assets.html)（`/`） |
| `/public/static` | 静态资源 |
| `/dist/` | 打包输出目录（执行 `yarn build` 后生成） |

## 前置条件

在开始之前，你应确保已安装并运行以下内容：

- [X] Yarn - [安装说明](https://yarnpkg.com/en/docs/install)
- [X] Vue CLI 3 - [安装说明](https://cli.vuejs.org/guide/installation.html)
- [X] Python 3 - [安装说明](https://wiki.python.org/moin/BeginnersGuide)
- [X] Pipenv - [安装说明](https://pipenv.readthedocs.io/en/latest/install/#installing-pipenv)

## 设置模板

```
$ git clone https://github.com/gtalarico/django-vue-template
$ cd django-vue-template
```

安装依赖
```
$ yarn install
$ pipenv install --dev && pipenv shell
$ python manage.py migrate
```

## 运行开发服务器

```
$ python manage.py runserver
```

在同一目录的另一个终端标签页中运行：

```
$ yarn serve
```

Vue 应用会通过 [`localhost:8080`](http://localhost:8080/) 提供服务，而 Django API 和静态文件则通过 [`localhost:8000`](http://localhost:8000/) 提供服务。

双开发服务器设置允许你利用 webpack 的开发服务器实现热模块替换（HMR）。
[`vue.config.js`](/vue.config.js) 中的代理配置会将请求转发回端口 8000 上的 Django API。

如果你更想运行单一开发服务器，也可以只让 Django 开发服务器监听 `:8000`，但需要先构建 Vue 应用；这样页面在修改后不会自动刷新。

```
$ yarn build
$ python manage.py runserver
```

## PyCharm 额外配置

按照此指南确保已经正确配置 pipenv

https://www.jetbrains.com/help/pycharm/pipenv.html

点击 "Edit Configurations"

在模板中选择 Django Server

点击 + 创建一个配置模板

在 Environment variables 中添加：

```
PYTHONUNBUFFERED=1;DJANGO_SETTINGS_MODULE=backend.settings.dev
```

点击 Apply，然后点击 Ok

## 部署

* 在 [`backend.settings.prod`](/backend/settings/prod.py) 中设置 `ALLOWED_HOSTS`

### Heroku 服务器

```
$ heroku apps:create django-vue-template-demo
$ heroku git:remote --app django-vue-template-demo
$ heroku buildpacks:add --index 1 heroku/nodejs
$ heroku buildpacks:add --index 2 heroku/python
$ heroku addons:create heroku-postgresql:hobby-dev
$ heroku config:set DJANGO_SETTINGS_MODULE=backend.settings.prod
$ heroku config:set DJANGO_SECRET_KEY='...(your django SECRET_KEY value)...'

$ git push heroku
```

Heroku 的 Node.js buildpack 会处理 [`package.json`](/package.json) 中的依赖安装。
随后会触发 `postinstall` 命令，执行 `yarn build`。
这会生成打包后的 `dist` 目录，并由 whitenoise 提供服务。

Python buildpack 会检测 [`Pipfile`](/Pipfile) 并安装所有 Python 依赖。

[`Procfile`](/Procfile) 会执行 Django 迁移，然后使用 gunicorn 启动 Django 应用，这符合 Heroku 的推荐方式。

##### Heroku 一键部署

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/gtalarico/django-vue-template)

## 静态资源

请查看 `settings.dev` 和 [`vue.config.js`](/vue.config.js) 中关于静态资源策略的说明。

这个模板实现了 Whitenoise Django 推荐的处理方式。
更多信息请参考 [WhiteNoise 文档](http://whitenoise.evans.io/en/stable/django.html)

它使用 Django Whitenoise 向 `/static/` 提供所有静态文件和 Vue 打包文件。
虽然这看起来效率不高，但通过添加 CDN（如 CloudFront）后，这个问题会立刻得到解决。
使用 [`vue.config.js`](/vue.config.js) 中的 `baseUrl` 配置，将所有资源指向 CDN，
然后让 CDN 的源站回源到你域名的 `/static` 地址。

Whitenoise 会在 CDN 上缓存静态文件一次，然后直接由 CDN 继续提供服务。

这使得部署非常简单，无需单独维护静态文件服务器。

[Cloudfront 设置 Wiki](https://github.com/gtalarico/django-vue-template/wiki/Setup-CDN-on-Cloud-Front)
