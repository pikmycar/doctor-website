import { Suspense, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Environment, Float, MeshTransmissionMaterial, Sphere, Torus } from '@react-three/drei'
import * as THREE from 'three'

function MedicalOrb() {
  const group = useRef<THREE.Group>(null)
  useFrame((state) => {
    if (!group.current) return
    group.current.rotation.y = THREE.MathUtils.lerp(group.current.rotation.y, state.pointer.x * 0.22, 0.04)
    group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, state.pointer.y * -0.12, 0.04)
  })
  return <group ref={group}>
    <Float speed={1.1} rotationIntensity={0.12} floatIntensity={0.35}>
      <Sphere args={[1.42, 32, 32]}><MeshTransmissionMaterial backside thickness={0.32} roughness={0.18} transmission={0.92} ior={1.35} chromaticAberration={0.08} color="#b7d6d4" /></Sphere>
      <Torus args={[1.72, 0.015, 8, 96]} rotation={[Math.PI / 2.7, 0.2, 0]}><meshBasicMaterial color="#c45c45" transparent opacity={0.7} /></Torus>
      <Torus args={[1.93, 0.008, 8, 96]} rotation={[0.8, Math.PI / 2, 0.4]}><meshBasicMaterial color="#173f3b" transparent opacity={0.35} /></Torus>
      {[[-1.1, .6, .85], [.9, .8, .5], [.6, -1, .7], [-.8, -.85, .2]].map((position, index) => <mesh key={index} position={position as [number, number, number]}><sphereGeometry args={[0.07, 12, 12]} /><meshStandardMaterial color={index % 2 ? '#c45c45' : '#fffdf8'} emissive={index % 2 ? '#762d20' : '#8fb9c5'} emissiveIntensity={0.5} /></mesh>)}
    </Float>
  </group>
}

export default function HeroScene() {
  return <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 5], fov: 42}}><ambientLight intensity={1.1} /><directionalLight position={[3, 4, 5]} intensity={3} color="#fff5e6" /><directionalLight position={[-4, -2, 1]} intensity={2} color="#8fb9c5" /><Suspense fallback={null}><MedicalOrb /><Environment preset="studio" /></Suspense></Canvas>
}