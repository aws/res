val smithyVersion: String by project

plugins {
    id("software.amazon.smithy.gradle.smithy-jar").version("1.3.0").apply(false)
}

subprojects {
    apply(plugin = "java")
    apply(plugin = "software.amazon.smithy.gradle.smithy-jar")

    repositories {
        mavenLocal()
        mavenCentral()
    }

    dependencies {
        "implementation"("software.amazon.smithy:smithy-aws-traits:$smithyVersion")
        "implementation"("software.amazon.smithy:smithy-model:$smithyVersion")
        "implementation"("software.amazon.smithy:smithy-linters:$smithyVersion")
        "implementation"("software.amazon.smithy:smithy-openapi:$smithyVersion")
    }

    tasks["jar"].enabled = false
}
