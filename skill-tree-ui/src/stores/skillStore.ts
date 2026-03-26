import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { wsService } from '../services/websocket'

export interface Skill {
  method_id: string
  name: string
  description: string
  quality: number
  quality_name: string
  realm_required: number
  realm_name: string
  exp_multiplier: number
  attack_bonus: number
  defense_bonus: number
  dao_yun_rate: number
  mastery_exp: number
  can_learn: boolean
  is_equipped: boolean
  current_mastery: number
  current_exp: number
}

export interface CombatSkill {
  gongfa_id: string
  name: string
  description: string
  tier: number
  tier_name: string
  attack_bonus: number
  defense_bonus: number
  hp_regen: number
  lingqi_regen: number
  lingqi_cost: number
  mastery_exp: number
  equipped_slot: string | null
  current_mastery: number
  current_exp: number
}

export interface SkillTree {
  tree_id: string
  name: string
  name_en: string
  desc: string
  stat: string
  skills: Skill[]
}

export interface CombatSkillGroup {
  name: string
  name_en: string
  skills: CombatSkill[]
}

export const useSkillStore = defineStore('skills', () => {
  const passiveSkills = ref<SkillTree[]>([])
  const combatSkills = ref<Record<string, CombatSkillGroup>>({})
  const availableSkills = ref<Skill[]>([])
  const selectedSkill = ref<Skill | null>(null)
  const selectedCombatSkill = ref<CombatSkill | null>(null)
  const loading = ref(false)
  const activeTab = ref<'passive' | 'combat'>('passive')
  const filterQuality = ref<number | null>(null)
  const filterRealm = ref<number | null>(null)
  const searchQuery = ref('')

  const filteredPassiveSkills = computed(() => {
    let skills = passiveSkills.value
    
    if (filterQuality.value !== null) {
      skills = skills.map(tree => ({
        ...tree,
        skills: tree.skills.filter(s => s.quality === filterQuality.value)
      })).filter(tree => tree.skills.length > 0)
    }
    
    if (filterRealm.value !== null) {
      skills = skills.map(tree => ({
        ...tree,
        skills: tree.skills.filter(s => s.realm_required === filterRealm.value)
      })).filter(tree => tree.skills.length > 0)
    }
    
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      skills = skills.map(tree => ({
        ...tree,
        skills: tree.skills.filter(s => 
          s.name.toLowerCase().includes(query) ||
          s.description.toLowerCase().includes(query)
        )
      })).filter(tree => tree.skills.length > 0)
    }
    
    return skills
  })

  const filteredCombatSkills = computed(() => {
    let skills = combatSkills.value
    
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      const filtered: Record<string, CombatSkillGroup> = {}
      for (const [key, group] of Object.entries(skills)) {
        const filteredGroupSkills = group.skills.filter(s =>
          s.name.toLowerCase().includes(query) ||
          s.description.toLowerCase().includes(query)
        )
        if (filteredGroupSkills.length > 0) {
          filtered[key] = { ...group, skills: filteredGroupSkills }
        }
      }
      skills = filtered
    }
    
    return skills
  })

  const equippedSkillsCount = computed(() => {
    return passiveSkills.value.reduce((count, tree) => {
      return count + tree.skills.filter(s => s.is_equipped).length
    }, 0)
  })

  const equippedCombatSkillsCount = computed(() => {
    return Object.values(combatSkills.value).reduce((count, group) => {
      return count + group.skills.filter(s => s.equipped_slot !== null).length
    }, 0)
  })

  function setupMessageHandlers() {
    wsService.on('skill_trees_data', (data) => {
      passiveSkills.value = data as SkillTree[]
      loading.value = false
    })

    wsService.on('combat_skills_data', (data) => {
      combatSkills.value = data as Record<string, CombatSkillGroup>
      loading.value = false
    })

    wsService.on('available_skills_data', (data) => {
      availableSkills.value = data as Skill[]
      loading.value = false
    })

    wsService.on('skill_detail_data', (data) => {
      const skillData = data as { skill: Skill; mastery_levels: { level: number; exp: number; bonus: string }[] }
      selectedSkill.value = skillData.skill
    })

    wsService.on('skill_learned', (data) => {
      console.log('Skill learned:', data)
      fetchPassiveSkills()
    })

    wsService.on('skill_equipped', (data) => {
      console.log('Skill equipped:', data)
      fetchPassiveSkills()
    })
  }

  async function fetchPassiveSkills() {
    loading.value = true
    wsService.send('get_skill_trees')
  }

  async function fetchCombatSkills() {
    loading.value = true
    wsService.send('get_combat_skills')
  }

  async function fetchAvailableSkills() {
    loading.value = true
    wsService.send('get_available_skills')
  }

  async function learnSkill(methodId: string) {
    wsService.send('learn_skill', { method_id: methodId })
  }

  async function equipSkill(methodId: string) {
    wsService.send('equip_skill', { method_id: methodId })
  }

  async function unequipSkill() {
    wsService.send('unequip_skill')
  }

  function selectSkill(skill: Skill | null) {
    selectedSkill.value = skill
  }

  function selectCombatSkill(skill: CombatSkill | null) {
    selectedCombatSkill.value = skill
  }

  function setActiveTab(tab: 'passive' | 'combat') {
    activeTab.value = tab
    if (tab === 'passive' && passiveSkills.value.length === 0) {
      fetchPassiveSkills()
    } else if (tab === 'combat' && Object.keys(combatSkills.value).length === 0) {
      fetchCombatSkills()
    }
  }

  function setFilterQuality(quality: number | null) {
    filterQuality.value = quality
  }

  function setFilterRealm(realm: number | null) {
    filterRealm.value = realm
  }

  function setSearchQuery(query: string) {
    searchQuery.value = query
  }

  return {
    passiveSkills,
    combatSkills,
    availableSkills,
    selectedSkill,
    selectedCombatSkill,
    loading,
    activeTab,
    filterQuality,
    filterRealm,
    searchQuery,
    filteredPassiveSkills,
    filteredCombatSkills,
    equippedSkillsCount,
    equippedCombatSkillsCount,
    setupMessageHandlers,
    fetchPassiveSkills,
    fetchCombatSkills,
    fetchAvailableSkills,
    learnSkill,
    equipSkill,
    unequipSkill,
    selectSkill,
    selectCombatSkill,
    setActiveTab,
    setFilterQuality,
    setFilterRealm,
    setSearchQuery,
  }
})
