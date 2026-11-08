#include <QtCore/QCoreApplication>
#include <QtCore/QPluginLoader>
#include <QtCore/QJsonDocument>
#include <QtCore/QJsonObject>
#include <cstdio>
int main(int argc,char **argv){ QCoreApplication app(argc,argv); if(argc!=2)return 2; QPluginLoader loader(QString::fromLocal8Bit(argv[1])); bool loaded=loader.load(); QJsonObject result{{"loaded",loaded},{"error",loader.errorString()}}; auto bytes=QJsonDocument(result).toJson(QJsonDocument::Compact); std::puts(bytes.constData()); return loaded?0:1; }
